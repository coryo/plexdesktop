from PyQt5.QtWidgets import QMessageBox


def timestamp_from_ms(milliseconds):
    m, s = divmod(milliseconds / 1000, 60)
    h, m = divmod(m, 60)
    return "{:.0f}:{:02.0f}:{:02.0f}".format(h, m, s)


def msg_box(message, title='plexdesktop'):
    msg = QMessageBox()
    msg.setText(message)
    msg.setWindowTitle(title)
    msg.exec_()


def title(media_object):
    item_type = media_object.get('type', None)
    view_group = media_object.parent.get('viewGroup', None)
    mixed_parents = bool(int(media_object.parent.get('mixedParents', '0')))
    filters = bool(int(media_object.get('filters', '0')))
    is_library = media_object.parent.get('identifier', None) == 'com.plexapp.plugins.library'
    if filters or not is_library:
        t = media_object['title']
    else:
        if view_group == 'episode':
            t = ('{} - s{:02d}e{:02d} - {}'.format(media_object['grandparentTitle'],
                                                   int(media_object['parentIndex']),
                                                   int(media_object['index']),
                                                   media_object['title'])
                 if mixed_parents else
                 's{:02d}e{:02d} - {}'.format(int(media_object.parent['parentIndex']),
                                              int(media_object['index']),
                                              media_object['title']))
        elif view_group == 'season':
            t = ('{} - {}'.format(media_object.parent['parentTitle'], media_object['title'])
                 if mixed_parents else
                 media_object['title'])
        elif view_group == 'secondary':
            t = media_object['title']
        elif view_group == 'movie':
            t = '{} ({})'.format(media_object['title'], media_object['year'])
        elif view_group == 'album':
            t = '{} - {}'.format(media_object['parentTitle'], media_object['title'])
        elif view_group == 'track':
            t = media_object['title']
            if 'index' in media_object:
                t = str(media_object['index']) + ' - ' + t
        else:
            if item_type == 'episode':
                t = '{} - s{:02d}e{:02d} - {}'.format(media_object['grandparentTitle'],
                                                      int(media_object['parentIndex']),
                                                      int(media_object['index']),
                                                      media_object['title'])
            elif item_type == 'season':
                t = '{} - {}'.format(media_object['parentTitle'], media_object['title'])
            elif item_type == 'movie':
                t = '{} ({})'.format(media_object['title'], media_object['year'])
            else:
                t = media_object['title']
    return t
