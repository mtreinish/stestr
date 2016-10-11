
def timedelta_to_seconds(delta):
    """Return the number of seconds that make up the duration of a timedelta.
    """
    return (
        (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6)
        / float(10**6))
