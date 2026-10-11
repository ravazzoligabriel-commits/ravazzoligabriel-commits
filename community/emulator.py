"""Headless mGBA through its stable libretro ABI; no simulated frames."""
import ctypes as C
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image

BUTTONS = dict(B=0, SELECT=2, START=3, UP=4, DOWN=5, LEFT=6, RIGHT=7, A=8, L=10, R=11)
ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL = C.CFUNCTYPE(None)
INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]

class SystemInfo(C.Structure):
    _fields_ = [('name', C.c_char_p), ('version', C.c_char_p), ('extensions', C.c_char_p), ('fullpath', C.c_bool), ('block', C.c_bool)]

class Emulator:
    def __init__(self, library):
        self.library_hash = hashlib.sha256(Path(library).read_bytes()).hexdigest()
        self.lib = C.CDLL(str(Path(library).resolve()))
        self.keys, self.frames, self.image, self.pixel_format = set(), 0, None, 0
        self._directory = C.create_string_buffer(str(Path(library).resolve().parent).encode())
        self._callbacks = [ENV(self._environment), VIDEO(self._video), AUDIO(lambda l,r: None),
                           BATCH(lambda data,n: n), POLL(lambda: None), INPUT(self._input)]
        for name, cb in zip(('environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'), self._callbacks):
            fn = getattr(self.lib, 'retro_set_' + name)
            fn.argtypes = [type(cb)]
            fn(cb)
        self.lib.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.lib.retro_load_game.restype = C.c_bool
        self.lib.retro_serialize_size.restype = C.c_size_t
        for name in ('retro_serialize', 'retro_unserialize'):
            getattr(self.lib, name).argtypes = [C.c_void_p, C.c_size_t]
            getattr(self.lib, name).restype = C.c_bool
        self.lib.retro_get_memory_data.argtypes = [C.c_uint]
        self.lib.retro_get_memory_data.restype = C.c_void_p
        self.lib.retro_get_memory_size.argtypes = [C.c_uint]
        self.lib.retro_get_memory_size.restype = C.c_size_t
        self.lib.retro_get_system_info.argtypes = [C.POINTER(SystemInfo)]
        info = SystemInfo()
        self.lib.retro_get_system_info(C.byref(info))
        self.version = info.version.decode()
        if info.name.decode().lower() != 'mgba':
            raise ValueError('This engine requires mGBA')
        self.lib.retro_init()
        self.loaded = False
        self.closed = False

    def _environment(self, command, data):
        if command == 10:  # SET_PIXEL_FORMAT
            self.pixel_format = C.cast(data, C.POINTER(C.c_int))[0]
            return self.pixel_format in (0,1,2)
        if command in (9,31):  # system/save directory, no external BIOS required
            C.cast(data, C.POINTER(C.c_char_p))[0] = C.cast(self._directory, C.c_char_p)
            return True
        if command == 3:  # can dupe
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        if command == 17:
            C.cast(data, C.POINTER(C.c_bool))[0] = False
            return True
        return False

    def _input(self, port, device, index, button):
        return int(port == 0 and device == 1 and index == 0 and button in self.keys)

    def _video(self, data, width, height, pitch):
        if not data or data == C.c_void_p(-1).value:
            return
        raw = C.string_at(data, pitch * height)
        if self.pixel_format == 1:
            self.image = Image.frombytes('RGB', (width,height), raw, 'raw', 'BGRX', pitch)
        else:
            pixels = bytearray()
            for y in range(height):
                for x in range(width):
                    offset = y*pitch + x*2
                    value = int.from_bytes(raw[offset:offset+2], 'little')
                    if self.pixel_format == 2:
                        r,g,b = (value>>11)&31, (value>>5)&63, value&31
                        pixels.extend((r*255//31,g*255//63,b*255//31))
                    else:
                        r,g,b = (value>>10)&31,(value>>5)&31,value&31
                        pixels.extend((r*255//31,g*255//31,b*255//31))
            self.image = Image.frombytes('RGB',(width,height),bytes(pixels))

    def loadGame(self, path):
        if self.closed:
            raise ValueError('Create a new emulator after closing the core')
        if self.loaded:
            raise ValueError('Close the current core before loading another cartridge')
        self.rom_hash = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        self._rom = C.create_string_buffer(Path(path).read_bytes())
        self._rom_path = str(Path(path).resolve()).encode()
        info = GameInfo(self._rom_path, C.cast(self._rom,C.c_void_p), len(self._rom)-1, None)
        if not self.lib.retro_load_game(C.byref(info)):
            raise ValueError('mGBA rejected ROM')
        self.loaded = True
        return self.getSessionState()

    def advanceFrames(self, frames):
        if not self.loaded:
            raise ValueError('Load a cartridge before advancing frames')
        if type(frames) is not int or not 1 <= frames <= 3600:
            raise ValueError('Frame count must be 1..3600')
        for _ in range(frames):
            self.lib.retro_run()
        self.frames += frames
        return self.getSessionState()

    def holdButton(self, button, frames=12):
        if button not in BUTTONS or type(frames) is not int or not 1 <= frames <= 120:
            raise ValueError('Invalid button/duration')
        self.keys = {BUTTONS[button]}
        try:
            return self.advanceFrames(frames)
        finally:
            self.keys.clear()

    def pressButton(self, button):
        self.holdButton(button, 1)
        return self.advanceFrames(2)

    def state(self):
        if not self.loaded:
            raise ValueError('Load a cartridge before serializing state')
        n = self.lib.retro_serialize_size()
        buffer = C.create_string_buffer(n)
        if not self.lib.retro_serialize(buffer,n):
            raise RuntimeError('mGBA serialization failed')
        return buffer.raw

    def restore(self, state):
        if not self.loaded:
            raise ValueError('Load a cartridge before restoring state')
        # mGBA libretro delays reset until first frame/serialization. Complete
        # that setup BEFORE unserialize, or the next run resets restored RAM.
        self.lib.retro_serialize_size()
        buffer = C.create_string_buffer(state)
        if not self.lib.retro_unserialize(buffer,len(state)):
            raise RuntimeError('mGBA restoration failed')
        self.keys.clear()

    def persistSave(self, path):
        data = self.battery()
        Path(path).write_bytes(data)
        return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

    @staticmethod
    def _savedata_section(state):
        # mGBA's GBA state struct is 0x61000 bytes, followed by <tag,size,offset>
        # extdata entries. Tag 2 is SAVEDATA. This is pinned/documented in
        # include/mgba/internal/gba/serialize.h and src/core/serialize.c.
        # After unserialize, libretro's exported SRAM pointer can be stale:
        # mGBA masks savedata with the snapshot's copy. Read the authoritative
        # savedata clone in a fresh serialization, not that frontend pointer.
        position = 0x61000
        for _ in range(300):
            if position + 16 > len(state):
                break
            tag,size,offset = struct.unpack_from('<IIQ',state,position)
            if tag == 0:
                return None
            if offset+size > len(state):
                raise ValueError('Invalid mGBA savedata extent')
            if tag == 2:
                return offset,size
            position += 16
        raise ValueError('Unsupported mGBA GBA snapshot format')

    def battery(self):
        state = self.state()
        section = self._savedata_section(state)
        return state[section[0]:section[0]+section[1]] if section else b''

    def loadSave(self, path):
        data = Path(path).read_bytes()
        state = bytearray(self.state())
        section = self._savedata_section(state)
        n = section[1] if section else 0
        if len(data) != n:
            raise ValueError('Battery save size mismatch')
        if n:
            state[section[0]:section[0]+n] = data
            self.restore(bytes(state))
        return dict(bytes=n,sha256=hashlib.sha256(data).hexdigest())

    def captureScreenshot(self, path):
        if self.image is None:
            raise RuntimeError('No emulator video frame')
        self.image.save(path)
        return dict(width=self.image.width,height=self.image.height,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())

    def getSessionState(self):
        return dict(emulator='mGBA',version=self.version,core_sha256=self.library_hash,
                    rom_sha256=getattr(self,'rom_hash',None),frames=self.frames)

    def close(self):
        if self.closed:
            return
        if self.loaded:
            self.lib.retro_unload_game()
            self.loaded = False
        self.lib.retro_deinit()
        self.closed = True
