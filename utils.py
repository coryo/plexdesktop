def timestamp_from_ms(milliseconds):
    m, s = divmod(milliseconds / 1000, 60)
    h, m = divmod(m, 60)
    return "{:.0f}:{:02.0f}:{:02.0f}".format(h, m, s)
