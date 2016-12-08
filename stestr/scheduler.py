# Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
# license at the users choice. A copy of both licenses are available in the
# project source as Apache-2.0 and BSD. You may not use this file except in
# compliance with one of these two licences.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# license you chose for the specific language governing permissions and
# limitations under that license.

import collections
import itertools
import multiprocessing
import operator


def partition_tests(test_ids, concurrency, repository, group_callback):
        """Parition test_ids by concurrency.

        Test durations from the repository are used to get partitions which
        have roughly the same expected runtime. New tests - those with no
        recorded duration - are allocated in round-robin fashion to the
        partitions created using test durations.

        :return: A list where each element is a distinct subset of test_ids,
            and the union of all the elements is equal to set(test_ids).
        """
        _group_callback = group_callback
        partitions = [list() for i in range(concurrency)]
        timed_partitions = [[0.0, partition] for partition in partitions]
        time_data = repository.get_test_times(test_ids)
        timed_tests = time_data['known']
        unknown_tests = time_data['unknown']
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
        return partitions


def local_concurrency():
    try:
        return multiprocessing.cpu_count()
    except NotImplementedError:
        # No concurrency logic known.
        return None
