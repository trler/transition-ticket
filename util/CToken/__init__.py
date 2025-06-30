import base64
import random
import time
from loguru import logger


class CTokenGenerator:
    def __init__(self, ticket_collection_t, time_offset, stay_time):
        self.touch_event = 0
        self.isibility_change = 0
        self.page_unload = 0
        self.timer = 0
        self.time_difference = 0
        self.scroll_x = 0
        self.scroll_y = 0
        self.inner_width = 0
        self.inner_height = 0
        self.outer_width = 0
        self.outer_height = 0
        self.screen_x = 0
        self.screen_y = 0
        self.screen_width = 0
        self.screen_height = 0
        self.screen_avail_width = 0
        self.ticket_collection_t = ticket_collection_t
        self.time_offset = time_offset
        self.stay_time = stay_time

    def encode(self):
        buffer = bytearray(16)
        data_mapping = {
            0: {'data': self.touch_event, 'length': 1},
            1: {'data': self.scroll_x, 'length': 1},
            2: {'data': self.isibility_change, 'length': 1},
            3: {'data': self.scroll_y, 'length': 1},
            4: {'data': self.inner_width, 'length': 1},
            5: {'data': self.page_unload, 'length': 1},
            6: {'data': self.inner_height, 'length': 1},
            7: {'data': self.outer_width, 'length': 1},
            8: {'data': self.timer, 'length': 2},
            10: {'data': self.time_difference, 'length': 2},
            12: {'data': self.outer_height, 'length': 1},
            13: {'data': self.screen_x, 'length': 1},
            14: {'data': self.screen_y, 'length': 1},
            15: {'data': self.screen_width, 'length': 1},
        }
        i = 0
        while i < 16:
            if i in data_mapping:
                mapping = data_mapping[i]
                if mapping['length'] == 1:
                    value = min(255, mapping['data']) if mapping['data'] > 0 else mapping['data']
                    buffer[i] = value & 0xFF
                    i += 1
                elif mapping['length'] == 2:
                    value = min(65535, mapping['data']) if mapping['data'] > 0 else mapping['data']
                    buffer[i] = (value >> 8) & 0xFF
                    buffer[i + 1] = value & 0xFF
                    i += 2
            else:
                condition_value = self.scroll_y if (4 & self.screen_height) else self.screen_avail_width
                buffer[i] = condition_value & 0xFF
                i += 1
        data_str = ''.join(chr(b) for b in buffer)
        return self.to_binary(data_str)

    def to_binary(self, data_str):
        uint16_data = []
        uint8_data = []
        # 第一次转换：字符串转为Uint16Array等价物
        for char in data_str:
            uint16_data.append(ord(char))
        # 第二次转换：Uint16Array buffer转为Uint8Array
        for val in uint16_data:
            uint8_data.append(val & 0xFF)
            uint8_data.append((val >> 8) & 0xFF)
        byte_data = bytes(uint8_data)
        return base64.b64encode(byte_data).decode('ascii')

    def generate_ctoken(self, type="createV2") -> str:
        self.touch_event = 255                              # 触摸事件数: 手机端抓包数据
        self.page_unload = 2                                # 页面卸载数: 手机端抓包数据
        self.isibility_change = 2                           # 可见性变化数: 手机端抓包数据
        self.inner_width = 255                              # 窗口内部宽度: 手机端抓包数据
        self.inner_height = 255                             # 窗口内部高度: 手机端抓包数据
        self.outer_width = 255                              # 窗口外部宽度: 手机端抓包数据
        self.outer_height = 255                             # 窗口外部高度: 手机端抓包数据
        self.screen_width = 255                             # 屏幕宽度: 手机端抓包数据
        self.screen_height = random.randint(1000, 3000)     # 屏幕高度: 用于条件判断
        self.screen_avail_width = random.randint(1, 100)    # 屏幕可用宽度: 用于条件判断
        if type == "createV2":
            # createV2阶段
            self.time_difference = int(time.time() + self.time_offset - self.ticket_collection_t)
            self.timer = int(self.time_difference + self.stay_time)
            self.page_unload = 25
        else:
            # prepare阶段
            self.time_difference = 0
            self.timer = int(self.stay_time)
            self.touch_event = random.randint(3, 10)
        return self.encode()


class CTokenDecoder:
    def decode_ctoken(self, ctoken):
        try:
            decoded_data = base64.b64decode(ctoken)
            # 1. 从Uint8Array buffer重建Uint16Array
            uint16_values = []
            for i in range(0, len(decoded_data), 2):
                if i + 1 < len(decoded_data):
                    # 小端序：低字节在前
                    low_byte = decoded_data[i]
                    high_byte = decoded_data[i + 1]
                    uint16_val = low_byte | (high_byte << 8)
                    uint16_values.append(uint16_val)
            # 2. 从Uint16Array重建原始字符串(16字节)
            original_bytes = []
            for val in uint16_values:
                original_bytes.append(val & 0xFF)
            if len(original_bytes) < 16:
                original_bytes.extend([0] * (16 - len(original_bytes)))
            elif len(original_bytes) > 16:
                original_bytes = original_bytes[:16]
            return original_bytes
        except Exception as e:
            print(f"解码错误: {e}")
            return None

    def parse_decoded_data(self, byte_data):
        if not byte_data or len(byte_data) < 16:
            return None
        result = {}
        result['f'] = byte_data[0]                              # 触摸事件数
        result['m'] = byte_data[1]                              # 水平滚动位置
        result['d'] = byte_data[2]                              # 可见性变化数
        result['y'] = byte_data[3]                              # 垂直滚动位置
        result['g'] = byte_data[4]                              # 窗口内部宽度
        result['p'] = byte_data[5]                              # 页面卸载数
        result['b'] = byte_data[6]                              # 窗口内部高度
        result['_'] = byte_data[7]                              # 窗口外部宽度
        result['h'] = (byte_data[8] << 8) | byte_data[9]        # 点进页面后的计时器(2字节，大端序)
        result['v'] = (byte_data[10] << 8) | byte_data[11]      # 时间差(2字节，大端序)
        result['w'] = byte_data[12]                             # 窗口外部高度
        result['A'] = byte_data[13]                             # 窗口屏幕X位置
        result['x'] = byte_data[14]                             # 窗口屏幕Y位置
        result['C'] = byte_data[15]                             # 屏幕宽度
        result['pos_9'] = byte_data[9]                          # h的低字节（大端序）
        result['pos_11'] = byte_data[11]                        # v的低字节（大端序）
        return result

    def print_analysis(self, ctoken):
        print(f"ctoken: {ctoken}")
        print()
        decoded = self.decode_ctoken(ctoken)
        if decoded:
            print(f"原始字节: {decoded}")
            hex_str = ' '.join([f'{b:02x}' for b in decoded])
            print(f"原始字节(hex): {hex_str}")
            print()
            parsed = self.parse_decoded_data(decoded)
            if parsed:
                field_names = {
                    'f': '触摸事件数',
                    'm': '水平滚动位置',
                    'd': '可见性变化数',
                    'y': '垂直滚动位置',
                    'g': '窗口内部宽度',
                    'p': '页面卸载数',
                    'b': '窗口内部高度',
                    '_': '窗口外部宽度',
                    'h': '点进页面后的计时器(秒)',
                    'v': '时间差(秒)',
                    'w': '窗口外部高度',
                    'A': '窗口屏幕X位置',
                    'x': '窗口屏幕Y位置',
                    'C': '屏幕宽度'
                }
                position_mapping = [
                    ('f', 0), ('m', 1), ('d', 2), ('y', 3),
                    ('g', 4), ('p', 5), ('b', 6), ('_', 7),
                    ('h', 8), ('v', 10), ('w', 12), ('A', 13),
                    ('x', 14), ('C', 15)
                ]
                for key, pos in position_mapping:
                    if key in parsed:
                        print(f"{key:<12} | 位置 {pos:2d} | 值: {parsed[key]:5d} | {field_names[key]}")
                print(f"{'pos_9':<12} | 位置  9 | 值: {parsed['pos_9']:5d} | h的低字节 (h={parsed['h']}, 高字节={parsed['h']>>8}, 低字节={parsed['h']&0xFF})")
                print(f"{'pos_11':<12} | 位置 11 | 值: {parsed['pos_11']:5d} | v的低字节 (v={parsed['v']}, 高字节={parsed['v']>>8}, 低字节={parsed['v']&0xFF})")
                print(f"\n字节验证（大端序）:")
                print(f"h={parsed['h']:5d} = 0x{parsed['h']:04x} → 高字节=0x{parsed['h']>>8:02x}({parsed['h']>>8:3d}), 低字节=0x{parsed['h']&0xFF:02x}({parsed['h']&0xFF:3d})")
                print(f"v={parsed['v']:5d} = 0x{parsed['v']:04x} → 高字节=0x{parsed['v']>>8:02x}({parsed['v']>>8:3d}), 低字节=0x{parsed['v']&0xFF:02x}({parsed['v']&0xFF:3d})")
                print(f"\n大端序存储验证:")
                print(f"位置8(h高字节)={decoded[8]}, 位置9(h低字节)={decoded[9]} → h={(decoded[8]<<8)|decoded[9]}")
                print(f"位置10(v高字节)={decoded[10]}, 位置11(v低字节)={decoded[11]} → v={(decoded[10]<<8)|decoded[11]}")
        else:
            print("解码失败")