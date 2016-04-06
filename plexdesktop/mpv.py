from ctypes import *
import platform

if platform.system() == 'Windows':
    backend = CDLL('mpv-1.dll')
elif platform.system() == 'Linux':
    backend = CDLL('libmpv.so.1')
elif platform.system() == 'Darwin':
    backend = CDLL('libmpv.dylib')


class MpvHandle(c_void_p):
    pass


class ErrorCode:
    """ For documentation on these, see mpv's libmpv/client.h """
    SUCCESS                 = 0
    EVENT_QUEUE_FULL        = -1
    NOMEM                   = -2
    UNINITIALIZED           = -3
    INVALID_PARAMETER       = -4
    OPTION_NOT_FOUND        = -5
    OPTION_FORMAT           = -6
    OPTION_ERROR            = -7
    PROPERTY_NOT_FOUND      = -8
    PROPERTY_FORMAT         = -9
    PROPERTY_UNAVAILABLE    = -10
    PROPERTY_ERROR          = -11
    COMMAND                 = -12

    EXCEPTION_DICT = {
             0:     None,
            -1:     lambda *a: MemoryError('mpv event queue full', *a),
            -2:     lambda *a: MemoryError('mpv cannot allocate memory', *a),
            -3:     lambda *a: ValueError('Uninitialized mpv handle used', *a),
            -4:     lambda *a: ValueError('Invalid value for mpv parameter', *a),
            -5:     lambda *a: AttributeError('mpv option does not exist', *a),
            -6:     lambda *a: TypeError('Tried to set mpv option using wrong format', *a),
            -7:     lambda *a: ValueError('Invalid value for mpv option', *a),
            -8:     lambda *a: AttributeError('mpv property does not exist', *a),
            -9:     lambda *a: TypeError('Tried to set mpv property using wrong format', *a),
            -10:    lambda *a: AttributeError('mpv property is not available', *a),
            -11:    lambda *a: ValueError('Invalid value for mpv property', *a),
            -12:    lambda *a: SystemError('Error running mpv command', *a)
        }

    @classmethod
    def DEFAULT_ERROR_HANDLER(ec, *args):
        return ValueError(_mpv_error_string(ec).decode(), ec, *a)

    @classmethod
    def raise_for_ec(kls, func, *args):
        ec = func(*args)
        ex = kls.EXCEPTION_DICT.get(ec, kls.DEFAULT_ERROR_HANDLER)
        if ex:
            raise ex(ec, *args)


class MpvFormat(c_int):
    NONE        = 0
    STRING      = 1
    OSD_STRING  = 2
    FLAG        = 3
    INT64       = 4
    DOUBLE      = 5
    NODE        = 6
    NODE_ARRAY  = 7  # Used by NODE
    NODE_MAP    = 8  # Used by NODE
    BYTE_ARRAY  = 9  # Used by NODE

    def __repr__(self):
        return ['NONE', 'STRING', 'OSD_STRING', 'FLAG', 'INT64', 'DOUBLE',
                'NODE', 'NODE_ARRAY', 'NODE_MAP', 'BYTE_ARRAY'][self.value]

    @staticmethod
    def ctype(value):
        return [None, c_char_p, c_char_p, c_int, c_longlong, c_double, MpvNode,
                MpvNodeList, MpvNodeList, MpvByteArray][value]



class MpvEventID(c_int):
    NONE                    = 0
    SHUTDOWN                = 1
    LOG_MESSAGE             = 2
    GET_PROPERTY_REPLY      = 3
    SET_PROPERTY_REPLY      = 4
    COMMAND_REPLY           = 5
    START_FILE              = 6
    END_FILE                = 7
    FILE_LOADED             = 8
    TRACKS_CHANGED          = 9
    TRACK_SWITCHED          = 10
    IDLE                    = 11
    PAUSE                   = 12
    UNPAUSE                 = 13
    TICK                    = 14
    SCRIPT_INPUT_DISPATCH   = 15
    CLIENT_MESSAGE          = 16
    VIDEO_RECONFIG          = 17
    AUDIO_RECONFIG          = 18
    METADATA_UPDATE         = 19
    SEEK                    = 20
    PLAYBACK_RESTART        = 21
    PROPERTY_CHANGE         = 22
    CHAPTER_CHANGE          = 23

    ANY = ( SHUTDOWN, LOG_MESSAGE, GET_PROPERTY_REPLY, SET_PROPERTY_REPLY, COMMAND_REPLY, START_FILE, END_FILE,
            FILE_LOADED, TRACKS_CHANGED, TRACK_SWITCHED, IDLE, PAUSE, UNPAUSE, TICK, SCRIPT_INPUT_DISPATCH,
            CLIENT_MESSAGE, VIDEO_RECONFIG, AUDIO_RECONFIG, METADATA_UPDATE, SEEK, PLAYBACK_RESTART, PROPERTY_CHANGE,
            CHAPTER_CHANGE )


class MpvEvent(Structure):
    _fields_ = [('event_id', MpvEventID),
                ('error', c_int),
                ('reply_userdata', c_ulonglong),
                ('data', c_void_p)]

    def as_dict(self):
        dtype = {MpvEventID.END_FILE:               MpvEventEndFile,
                MpvEventID.PROPERTY_CHANGE:         MpvEventProperty,
                MpvEventID.GET_PROPERTY_REPLY:      MpvEventProperty,
                MpvEventID.LOG_MESSAGE:             MpvEventLogMessage,
                MpvEventID.SCRIPT_INPUT_DISPATCH:   MpvEventScriptInputDispatch,
                MpvEventID.CLIENT_MESSAGE:          MpvEventClientMessage
            }.get(self.event_id.value, None)
        return {'event_id': self.event_id.value,
                'error': self.error,
                'reply_userdata': self.reply_userdata,
                'event': cast(self.data, POINTER(dtype)).contents.as_dict() if dtype else None}


class MpvEventProperty(Structure):
    _fields_ = [('name', c_char_p),
                ('format', MpvFormat),
                ('data', c_void_p)]

    def as_dict(self):
        dpointer = cast(self.data, POINTER(MpvFormat.ctype(self.format.value)))
        if self.format.value == MpvFormat.NONE:
            data = None
        elif self.format.value == MpvFormat.NODE:
            data = dpointer.contents.get_value()
        elif self.format.value == MpvFormat.STRING:
            data = dpointer.contents.value.decode()
        else:
            data = dpointer.contents.value
        return {'name': self.name.decode(),
                'format': self.format,
                'data': data}


class MpvNodeList(Structure):

    def as_list(self):
        return [self.values[i] for i in range(self.num)]

    def as_dict(self):
        return {self.keys[i].decode(): self.values[i] for i in range(self.num)}


class MpvByteArray(Structure):
    _fields_ = [('data', c_void_p),
                ('size', c_size_t)]


class _MpvNodeUnion(Union):
    _fields_ = [('string', c_char_p),
                ('flag', c_int),
                ('int64', c_longlong),
                ('double_', c_double),
                ('list', POINTER(MpvNodeList)),
                ('ba', POINTER(MpvByteArray))]


class MpvNode(Structure):
    _anonymous_ = ('u',)
    _fields_ = [('u', _MpvNodeUnion),
                ('format', MpvFormat)]

    def get_value(self):
        # this doesn't work with {}[] instead of if statements.
        if self.format.value in [MpvFormat.STRING, MpvFormat.OSD_STRING]:
            return self.string.decode()
        elif self.format.value == MpvFormat.FLAG:
            return bool(self.flag)
        elif self.format.value == MpvFormat.INT64:
            return self.int64
        elif self.format.value == MpvFormat.DOUBLE:
            return self.double_
        elif self.format.value == MpvFormat.NODE_ARRAY:
            return [node.get_value() for node in self.list.contents.as_list()]
        elif self.format.value == MpvFormat.NODE_MAP:
            return {key: node.get_value() for key, node in self.list.contents.as_dict().items()}
        elif self.format.value == MpvFormat.BYTE_ARRAY:
            raise NotImplementedError
        else:
            return None


MpvNodeList._fields_ = [('num', c_int),
                        ('values', POINTER(MpvNode)),
                        ('keys', POINTER(c_char_p))]


class MpvEventLogMessage(Structure):
    _fields_ = [('prefix', c_char_p),
                ('level', c_char_p),
                ('text', c_char_p)]

    def as_dict(self):
        return {name: getattr(self, name).decode().rstrip('\n') for name, _t in self._fields_}


class MpvEventEndFile(c_int):
    EOF_OR_INIT_FAILURE = 0
    RESTARTED           = 1
    ABORTED             = 2
    QUIT                = 3

    def as_dict(self):
        return {'reason': self.value}


class MpvEventScriptInputDispatch(Structure):
    _fields_ = [('arg0', c_int),
                ('type', c_char_p)]

    def as_dict(self):
        pass # TODO


class MpvEventClientMessage(Structure):
    _fields_ = [('num_args', c_int),
                ('args', POINTER(c_char_p))]

    def as_dict(self):
        return {'args': [self.args[i].value for i in range(self.num_args.value)]}

WakeupCallback = CFUNCTYPE(None, c_void_p)


def _handle_func(name, args=[], res=None):
    func = getattr(backend, name)
    if res is not None:
        func.restype = res
    func.argtypes = [MpvHandle] + args

    def wrapper(*args):
        if res is not None:
            return func(*args)
        else:
            ErrorCode.raise_for_ec(func, *args)
    globals()['_' + name] = wrapper


backend.mpv_client_api_version.restype = c_ulong


def _mpv_client_api_version():
    ver = backend.mpv_client_api_version()
    return ver >> 16, ver & 0xFFFF

backend.mpv_free.argtypes = [c_void_p]
_mpv_free = backend.mpv_free

backend.mpv_create.restype = MpvHandle
_mpv_create = backend.mpv_create

backend.mpv_free_node_contents.argtypes = [MpvNode]
_mpv_free_node_contents = backend.mpv_free_node_contents

_handle_func('mpv_create_client', [c_char_p], MpvHandle)
_handle_func('mpv_client_name', [], c_char_p)
_handle_func('mpv_initialize')
_handle_func('mpv_detach_destroy', [], c_int)
_handle_func('mpv_terminate_destroy', [], c_int)
_handle_func('mpv_load_config_file', [c_char_p])
_handle_func('mpv_suspend', [], c_int)
_handle_func('mpv_resume', [], c_int)
_handle_func('mpv_get_time_us', [], c_ulonglong)

_handle_func('mpv_set_option', [c_char_p, MpvFormat, c_void_p])
_handle_func('mpv_set_option_string', [c_char_p, c_char_p])

_handle_func('mpv_command', [POINTER(c_char_p)])
_handle_func('mpv_command_string', [c_char_p, c_char_p])
_handle_func('mpv_command_async', [c_ulonglong, POINTER(c_char_p)])

_handle_func('mpv_set_property', [c_char_p, MpvFormat, c_void_p])
_handle_func('mpv_set_property_string', [c_char_p, c_char_p])
_handle_func('mpv_set_property_async', [c_ulonglong, c_char_p, MpvFormat, c_void_p])
_handle_func('mpv_get_property', [c_char_p, MpvFormat, c_void_p])
_handle_func('mpv_get_property_string', [c_char_p], c_char_p)
_handle_func('mpv_get_property_osd_string', [c_char_p], c_char_p)
_handle_func('mpv_get_property_async', [c_ulonglong, c_char_p, MpvFormat])
_handle_func('mpv_observe_property', [c_ulonglong, c_char_p, MpvFormat])
_handle_func('mpv_unobserve_property', [c_ulonglong])

backend.mpv_event_name.restype = c_char_p
backend.mpv_event_name.argtypes = [c_int]
_mpv_event_name = backend.mpv_event_name

backend.mpv_error_string.restype = c_char_p
backend.mpv_error_string.argtypes = [c_int]
_mpv_error_string = backend.mpv_error_string

_handle_func('mpv_request_event', [MpvEventID, c_int])
_handle_func('mpv_request_log_messages', [c_char_p])
_handle_func('mpv_wait_event', [c_double], POINTER(MpvEvent))
_handle_func('mpv_wakeup', [], c_int)
_handle_func('mpv_set_wakeup_callback', [WakeupCallback, c_void_p], c_int)
_handle_func('mpv_get_wakeup_pipe', [], c_int)


def _ensure_encoding(possibly_bytes):
    return possibly_bytes.decode() if type(possibly_bytes) is bytes else possibly_bytes


def _event_generator(handle):
    while True:
        try:
            event = _mpv_wait_event(handle, -1).contents
        except OSError as e:
            raise StopIteration(str(e))
        if event.event_id.value == MpvEventID.NONE:
            raise StopIteration()
        yield event


def load_lua():
    """ Use this function if you intend to use mpv's built-in lua interpreter. This is e.g. needed for playback of
    youtube urls. """
    CDLL('liblua.so', mode=RTLD_GLOBAL)


class MPV:
    """ See man mpv(1) for the details of the implemented commands. """
    def __init__(self, **kwargs):
        """ Create an MPV instance.

        Any kwargs given will be passed to mpv as options. """
        self.handle = _mpv_create()

        _mpv_set_option_string(self.handle, b'audio-display', b'no')

        def istr(o):
            return ('yes' if o else 'no') if type(o) is bool else str(o)

        for k, v in kwargs.items():
            try:
                _mpv_set_option_string(self.handle, k.replace('_', '-').encode(), istr(v).encode())
            except Exception as e:
                pass
        _mpv_initialize(self.handle)

    def __del__(self):
        if self.handle:
            self.terminate()

    def terminate(self):
        self.handle, handle = None, self.handle
        _mpv_terminate_destroy(handle)

    def terminate_destroy(self):
        _mpv_terminate_destroy(self.handle)

    def detach_destroy(self):
        _mpv_detach_destroy(self.handle)

    def request_log_messages(self, level):
        _mpv_request_log_messages(self.handle, level.encode())

    def observe_property(self, name, mpv_format):
        _mpv_observe_property(self.handle, 0, name.encode(), mpv_format)

    def command(self, name, *args):
        """ Execute a raw command """
        args = [name.encode()] + [str(arg).encode() for arg in args if arg is not None] + [None]
        _mpv_command(self.handle, (c_char_p * len(args))(*args))

    def seek(self, amount, reference="relative", precision="default-precise"):
        self.command('seek', amount, reference, precision)

    def revert_seek(self):
        self.command('revert_seek')

    def frame_step(self):
        self.command('frame_step')

    def frame_back_step(self):
        self.command('frame_back_step')

    def _add_property(self, name, value=None):
        self.command('add_property', name, value)

    def _cycle_property(self, name, direction='up'):
        self.command('cycle_property', name, direction)

    def _multiply_property(self, name, factor):
        self.command('multiply_property', name, factor)

    def screenshot(self, includes='subtitles', mode='single'):
        self.command('screenshot', includes, mode)

    def screenshot_to_file(self, filename, includes='subtitles'):
        self.command('screenshot_to_file', filename, includes)

    def playlist_next(self, mode='weak'):
        self.command('playlist_next', mode)

    def playlist_prev(self, mode='weak'):
        self.command('playlist_prev', mode)

    def loadfile(self, filename, mode='replace'):
        self.command('loadfile', filename, mode)

    def loadlist(self, playlist, mode='replace'):
        self.command('loadlist', playlist, mode)

    def playlist_clear(self):
        self.command('playlist_clear')

    def playlist_remove(self, index='current'):
        self.command('playlist_remove', index)

    def playlist_move(self, index1, index2):
        self.command('playlist_move', index1, index2)

    def run(self, command, *args):
        self.command('run', command, *args)

    def quit(self, code=None):
        self.command('quit', code)

    def quit_watch_later(self, code=None):
        self.command('quit_watch_later', code)

    def sub_add(self, filename):
        self.command('sub_add', filename)

    def sub_remove(self, sub_id=None):
        self.command('sub_remove', sub_id)

    def sub_reload(self, sub_id=None):
        self.command('sub_reload', sub_id)

    def sub_step(self, skip):
        self.command('sub_step', skip)

    def sub_seek(self, skip):
        self.command('sub_seek', skip)

    def toggle_osd(self):
        self.command('osd')

    def show_text(self, string, duration='-', level=None):
        self.command('show_text', string, duration, level)

    def show_progress(self):
        self.command('show_progress')

    def discnav(self, command):
        self.command('discnav', command)

    def write_watch_later_config(self):
        self.command('write_watch_later_config')

    def overlay_add(self, overlay_id, x, y, file_or_fd, offset, fmt, w, h, stride):
        self.command('overlay_add', overlay_id, x, y, file_or_fd, offset, fmt, w, h, stride)

    def overlay_remove(self, overlay_id):
        self.command('overlay_remove', overlay_id)

    def script_message(self, *args):
        self.command('script_message', *args)

    def script_message_to(self, target, *args):
        self.command('script_message_to', target, *args)

    # Convenience functions
    def play(self, filename):
        self.loadfile(filename)

    def stop(self):
        self.command('stop')

    def _get_property(self, prop, mpv_format):
        if mpv_format == MpvFormat.NONE:
            return None
        res = MpvFormat.ctype(mpv_format)()
        _mpv_get_property(self.handle, prop.encode(), mpv_format, addressof(res))
        if mpv_format in [MpvFormat.STRING, MpvFormat.OSD_STRING]:
            data = _ensure_encoding(res.value)
            _mpv_free(res)
            return data
        elif mpv_format == MpvFormat.FLAG:
            return bool(res.value)
        elif mpv_format == MpvFormat.INT64:
            return int(res.value)
        elif mpv_format == MpvFormat.DOUBLE:
            return float(res.value)
        elif mpv_format == MpvFormat.NODE:
            data = res.get_value()
            _mpv_free_node_contents(res)
            return data

    def _set_property(self, prop, mpv_format, value):
        if mpv_format == MpvFormat.NONE:
            return None
        val = MpvFormat.ctype(mpv_format)()
        if mpv_format in [MpvFormat.STRING, MpvFormat.OSD_STRING]:
            val.value = value.encode()
        elif mpv_format == MpvFormat.FLAG:
            val.value = int(value)
        elif mpv_format == MpvFormat.INT64:
            val.value = int(res)
        elif mpv_format == MpvFormat.DOUBLE:
            val.value = float(value)
        elif mpv_format == MpvFormat.NODE:
            raise NotImplementedError
        _mpv_set_property(self.handle, prop.encode(), mpv_format, addressof(val))


ALL_PROPERTIES = {
    'aid':                         (MpvFormat.STRING, 'rw'),
    'angle':                       (MpvFormat.INT64,  'rw'),
    'ass-style-override':          (MpvFormat.STRING, 'rw'),
    'ass-use-margins':             (MpvFormat.FLAG,   'rw'),
    'ass-vsfilter-aspect-compat':  (MpvFormat.FLAG,   'rw'),
    'audio':                       (MpvFormat.STRING, 'rw'), # alias for aid
    'audio-bitrate':               (MpvFormat.DOUBLE, 'r'),
    'audio-channels':              (MpvFormat.STRING, 'r'),
    'audio-codec':                 (MpvFormat.STRING, 'r'),
    'audio-delay':                 (MpvFormat.DOUBLE, 'rw'),
    'audio-format':                (MpvFormat.STRING, 'r'),
    'audio-samplerate':            (MpvFormat.INT64,  'r'),
    'avsync':                      (MpvFormat.DOUBLE, 'r'),
    'balance':                     (MpvFormat.DOUBLE, 'rw'),
    'border':                      (MpvFormat.FLAG,   'rw'),
    'brightness':                  (MpvFormat.INT64,  'rw'),
    'cache':                       (MpvFormat.INT64,  'r'),
    'cache-size':                  (MpvFormat.INT64,  'rw'),
    'chapter':                     (MpvFormat.INT64,  'rw'),
    'chapters':                    (MpvFormat.INT64,  'r'),
    'colormatrix':                 (MpvFormat.STRING, 'rw'),
    'colormatrix-input-range':     (MpvFormat.STRING, 'rw'),
    'colormatrix-output-range':    (MpvFormat.STRING, 'rw'),
    'colormatrix-primaries':       (MpvFormat.STRING, 'rw'),
    'contrast':                    (MpvFormat.INT64,  'rw'),
    'core-idle':                   (MpvFormat.FLAG,   'r'),
    'deinterlace':                 (MpvFormat.STRING, 'rw'),
    'dheight':                     (MpvFormat.INT64,  'r'),
    'disc-menu-active':            (MpvFormat.FLAG,   'r'),
    'disc-title':                  (MpvFormat.STRING, 'rw'),
    'disc-titles':                 (MpvFormat.INT64,  'r'),
    'drop-frame-count':            (MpvFormat.INT64,  'r'),
    'dwidth':                      (MpvFormat.INT64,  'r'),
    'edition':                     (MpvFormat.INT64,  'rw'),
    'editions':                    (MpvFormat.INT64,  'r'),
    'eof-reached':                 (MpvFormat.FLAG,   'r'),
    'estimated-vf-fps':            (MpvFormat.DOUBLE, 'r'),
    'file-size':                   (MpvFormat.INT64,  'r'),
    'filename':                    (MpvFormat.STRING, 'r'),
    'fps':                         (MpvFormat.DOUBLE, 'r'),
    'framedrop':                   (MpvFormat.STRING, 'rw'),
    'fullscreen':                  (MpvFormat.FLAG,   'rw'),
    'gamma':                       (MpvFormat.DOUBLE, 'rw'),
    'height':                      (MpvFormat.INT64,  'r'),
    'hr-seek':                     (MpvFormat.FLAG,   'rw'),
    'hue':                         (MpvFormat.INT64,  'rw'),
    'hwdec':                       (MpvFormat.FLAG,   'rw'),
    'length':                      (MpvFormat.DOUBLE, 'r'),
    'loop':                        (MpvFormat.STRING, 'rw'),
    'loop-file':                   (MpvFormat.STRING, 'rw'),
    'media-title':                 (MpvFormat.STRING, 'r'),
    'mute':                        (MpvFormat.FLAG,   'rw'),
    'ontop':                       (MpvFormat.FLAG,   'rw'),
    'osd-height':                  (MpvFormat.INT64,  'r'),
    'osd-level':                   (MpvFormat.INT64,  'rw'),
    'osd-par':                     (MpvFormat.DOUBLE, 'r'),
    'osd-scale':                   (MpvFormat.DOUBLE, 'rw'),
    'osd-width':                   (MpvFormat.INT64,   'r'),
    'panscan':                     (MpvFormat.DOUBLE, 'rw'),
    'path':                        (MpvFormat.STRING, 'r'),
    'pause':                       (MpvFormat.FLAG,   'rw'),
    'pause-for-cache':             (MpvFormat.FLAG,   'r'),
    'percent-pos':                 (MpvFormat.DOUBLE, 'rw'),
    'playlist-count':              (MpvFormat.INT64,  'r'),
    'playlist-pos':                (MpvFormat.INT64,  'rw'),
    'playtime-remaining':          (MpvFormat.DOUBLE, 'r'),
    'program':                     (MpvFormat.INT64,  'w'),
    'pts-association-mode':        (MpvFormat.STRING, 'rw'),
    'quvi-format':                 (MpvFormat.STRING, 'rw'),
    'ratio-pos':                   (MpvFormat.DOUBLE, 'rw'),
    'saturation':                  (MpvFormat.INT64,  'rw'),
    'secondary-sid':               (MpvFormat.STRING, 'rw'),
    'seekable':                    (MpvFormat.FLAG,   'r'),
    'sid':                         (MpvFormat.STRING, 'rw'),
    'speed':                       (MpvFormat.DOUBLE, 'rw'),
    'stream-capture':              (MpvFormat.STRING, 'rw'),
    'stream-end':                  (MpvFormat.INT64,  'r'),
    'stream-pos':                  (MpvFormat.INT64,  'rw'),
    'sub':                         (MpvFormat.STRING, 'rw'), # alias for sid
    'sub-delay':                   (MpvFormat.DOUBLE, 'rw'),
    'sub-forced-only':             (MpvFormat.FLAG,   'rw'),
    'sub-pos':                     (MpvFormat.INT64,  'rw'),
    'sub-scale':                   (MpvFormat.DOUBLE, 'rw'),
    'sub-visibility':              (MpvFormat.FLAG,   'rw'),
    'time-pos':                    (MpvFormat.DOUBLE, 'rw'),
    'time-remaining':              (MpvFormat.DOUBLE, 'r'),
    'time-start':                  (MpvFormat.DOUBLE, 'r'),
    'total-avsync-change':         (MpvFormat.DOUBLE, 'r'),
    'tv-brightness':               (MpvFormat.INT64,  'rw'),
    'tv-contrast':                 (MpvFormat.INT64,  'rw'),
    'tv-hue':                      (MpvFormat.INT64,  'rw'),
    'tv-saturation':               (MpvFormat.INT64,  'rw'),
    'vid':                         (MpvFormat.STRING, 'rw'),
    'video':                       (MpvFormat.STRING, 'rw'), # alias for vid
    'video-align-x':               (MpvFormat.DOUBLE, 'rw'),
    'video-align-y':               (MpvFormat.DOUBLE, 'rw'),
    'video-aspect':                (MpvFormat.STRING, 'rw'),
    'video-bitrate':               (MpvFormat.DOUBLE, 'r'),
    'video-codec':                 (MpvFormat.STRING, 'r'),
    'video-format':                (MpvFormat.STRING, 'r'),
    'video-pan-x':                 (MpvFormat.INT64,  'rw'),
    'video-pan-y':                 (MpvFormat.INT64,  'rw'),
    'video-unscaled':              (MpvFormat.FLAG,   'w'),
    'video-zoom':                  (MpvFormat.DOUBLE, 'rw'),
    'volume':                      (MpvFormat.DOUBLE, 'rw'),
    'width':                       (MpvFormat.INT64,  'r'),
    'window-scale':                (MpvFormat.DOUBLE, 'rw'),
    # Node Properties
    'metadata':                    (MpvFormat.NODE,   'r'),
    'chapter-metadata':            (MpvFormat.NODE,   'r'),
    'vf-metadata':                 (MpvFormat.NODE,   'r'),
    'af-metadata':                 (MpvFormat.NODE,   'r'),
    'video-params':                (MpvFormat.NODE,   'r'),
    'video-out-params':            (MpvFormat.NODE,   'r'),
    'playlist':                    (MpvFormat.NODE,   'r'),
    'track-list':                  (MpvFormat.NODE,   'r'),
    'chapter-list':                (MpvFormat.NODE,   'r'),
}


def bindproperty(MPV, name, proptype, access):

    def getter(self):
        cval = self._get_property(name, proptype)
        return cval

    def setter(self, value):
        self._set_property(name, proptype, value)

    def barf(*args):
        raise NotImplementedError('Access denied')

    setattr(MPV, name.replace('-', '_'), property(getter if 'r' in access else barf, setter if 'w' in access else barf))


for name, (proptype, access) in ALL_PROPERTIES.items():
    bindproperty(MPV, name, proptype, access)
