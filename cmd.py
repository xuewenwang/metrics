#!/bin/env python3
# Copyright 2022, Collabora, Ltd.
# SPDX-License-Identifier: BSL-1.0

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

import proto.monado_metrics_pb2
from google.protobuf.internal.decoder import _DecodeVarint as decodeVariant
from google.protobuf.internal.encoder import _EncodeVarint as encodeVariant

App = proto.monado_metrics_pb2.App
Record = proto.monado_metrics_pb2.Record
record = Record()

file = 'out/bloop.bin'

def writeMsg(f, msg):
    str = msg.SerializeToString()
    encodeVariant(f.write, len(str), True)
    f.write(str)


def writeBin():
    try:
        f = open(file, 'wb')
        r = Record()
        r.app.id = 1;
        r.app.predicted_display_time_ns = 2
        writeMsg(f, r)
        r.compositor.id = 1;
        writeMsg(f, r)
        r.app.id = 3;
        r.app.predicted_display_time_ns = 2
        writeMsg(f, r)
        f.close()
    except IOError:
        print("Error")

def readBin():
    data=None
    try:
        f = open(file, 'rb')
        data = f.read()
        f.close()
    except IOError:
        print("Error")

    r = Record()
    next_pos, pos = 0, 0
    while pos < len(data):
        next_pos, pos = decodeVariant(data, pos)
        r.ParseFromString(data[pos:pos + next_pos])
        print(r.WhichOneof('record'))
        pos += next_pos

writeBin()
readBin()
