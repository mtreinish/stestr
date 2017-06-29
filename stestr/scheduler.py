# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
import itertools
import multiprocessing
import operator
import random

import yaml

from stestr import selection


def partition_tests(test_ids, concurrency, repository, group_callback,
                    randomize=False):
        """Partition test_ids by concurrency.

        Test durations from the repository are used to get partitions which
        have roughly the same expected runtime. New tests - those with no
        recorded duration - are allocated in round-robin fashion to the
        partitions created using test durations.

        :param list test_ids: The list of test_ids to be partitioned
        :param int concurrency: The concurrency that will be used for running
            the tests. This is the number of partitions that test_ids will be
            split into.
        :param repository: A repository object that
        :param group_callback: A callback function that is used as a scheduler
            hint to group test_ids together and treat them as a single unit for
            scheduling. This function expects a single test_id parameter and it
            will return a group identifier. Tests_ids that have the same group
            identifier will be kept on the same worker.
        :param bool randomize: If true each partition's test order will be
                            randomized

        :return: A list where each element is a distinct subset of test_ids,
            and the union of all the elements is equal to set(test_ids).
        """
        _group_callback = group_callback
        partitions = [list() for i in range(concurrency)]
        timed_partitions = [[0.0, partition] for partition in partitions]
        time_data = {}
        if repository:
            time_data = repository.get_test_times(test_ids)
            timed_tests = time_data['known']
            unknown_tests = time_data['unknown']
        else:
            timed_tests = {}
            unknown_tests = set(test_ids)
        # Group tests: generate group_id -> test_ids.
        group_ids = collections.defaultdict(list)
        if _group_callback is None:
            group_callback = lambda _: None
        else:
            group_callback = _group_callback
        for test_id in test_ids:
            group_id = group_callback(test_id) or test_id
            group_ids[group_id].append(test_id)
        # Time groups: generate three sets of groups:
        # - fully timed dict(group_id -> time),
        # - partially timed dict(group_id -> time) and
        # - unknown (set of group_id)
        # We may in future treat partially timed different for scheduling, but
        # at least today we just schedule them after the fully timed groups.
        timed = {}
        partial = {}
        unknown = []
        for group_id, group_tests in group_ids.items():
            untimed_ids = unknown_tests.intersection(group_tests)
            group_time = sum(
                [timed_tests[test_id]
                    for test_id in untimed_ids.symmetric_difference(
                        group_tests)])
            if not untimed_ids:
                timed[group_id] = group_time
            elif group_time:
                partial[group_id] = group_time
            else:
                unknown.append(group_id)

        # Scheduling is NP complete in general, so we avoid aiming for
        # perfection. A quick approximation that is sufficient for our general
        # needs:
        # sort the groups by time
        # allocate to partitions by putting each group in to the partition with
        # the current (lowest time, shortest length[in tests])
        def consume_queue(groups):
            queue = sorted(
                groups.items(), key=operator.itemgetter(1), reverse=True)
            for group_id, duration in queue:
                timed_partitions[0][0] = timed_partitions[0][0] + duration
                timed_partitions[0][1].extend(group_ids[group_id])
                timed_partitions.sort(key=lambda item: (item[0], len(item[1])))

        consume_queue(timed)
        consume_queue(partial)
        # Assign groups with entirely unknown times in round robin fashion to
        # the partitions.
        for partition, group_id in zip(itertools.cycle(partitions), unknown):
            partition.extend(group_ids[group_id])
        if randomize:
            out_parts = []
            for partition in partitions:
                temp_part = list(partition)
                random.shuffle(temp_part)
                out_parts.append(list(temp_part))
            return out_parts
        else:
            return partitions


def local_concurrency():
    """Get the number of available CPUs on the system.

    :return: An int for the number of cpus. Or None if it couldn't be found
    """

    try:
        return multiprocessing.cpu_count()
    except NotImplementedError:
        # No concurrency logic known.
        return None


def generate_worker_partitions(ids, worker_path, repository=None,
                               group_callback=None, randomize=False):
    """Parse a worker yaml file and generate test groups

    :param list ids: A list of test ids too be partitioned
    :param path worker_path: The path to a worker file
    :param repository: A repository object that will be used for looking up
        timing data. This is optional, and also will only be used for
        scheduling if there is a count field on a worker.
    :param group_callback: A callback function that is used as a scheduler
        hint to group test_ids together and treat them as a single unit for
        scheduling. This function expects a single test_id parameter and it
        will return a group identifier. Tests_ids that have the same group
        identifier will be kept on the same worker. This is optional and
        also will only be used for scheduling if there is a count field on a
        worker.
    :param bool randomize: If true each partition's test order will be
        randomized. This is optional and also will only be used for scheduling
        if there is a count field on a worker.

    :returns: A list where each element is a distinct subset of test_ids.
    """
    with open(worker_path, 'r') as worker_file:
        workers_desc = yaml.load(worker_file.read())
    worker_groups = []
    for worker in workers_desc:
        if isinstance(worker, dict) and 'worker' in worker.keys():
            if isinstance(worker['worker'], list):
                local_worker_list = selection.filter_tests(
                    worker['worker'], ids)

                if 'concurrency' in worker.keys() and worker[
                    'concurrency'] > 1:
                    partitioned_tests = partition_tests(
                        local_worker_list, worker['concurrency'], repository,
                        group_callback, randomize)
                    worker_groups.extend(partitioned_tests)
                else:
                    # If a worker partition is empty don't add it to the output
                    if local_worker_list:
                        worker_groups.append(local_worker_list)
            else:
                raise TypeError('The input yaml is the incorrect format')
        else:
            raise TypeError('The input yaml is the incorrect format')
    return worker_groups
