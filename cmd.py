#!/bin/env python3
# Copyright 2022, Collabora, Ltd.
# SPDX-License-Identifier: BSL-1.0

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from dataclasses import dataclass
from proto.monado_metrics_pb2 import Record
from google.protobuf.internal.decoder import _DecodeVarint as decodeVariant
from google.protobuf.internal.encoder import _EncodeVarint as encodeVariant

import bokeh.io
import bokeh.layouts
import bokeh.models
import bokeh.palettes
import bokeh.plotting


@dataclass
class Metrics:
    """
    A collection of metrics.
    """

    frame_ids: list
    absolute: dict[str, list[float]]
    relative_gpu: dict[str, list[float]]
    relative_display: dict[str, list[float]]
    session_frames: list
    compositor_frames: list

    def __init__(self):
        self.frames = list()
        self.frame_ids = list()
        self.absolute = dict()
        self.absolute['cpu_ms'] = list()
        self.absolute['draw_ms'] = list()
        self.absolute['gpu_ms'] = list()
        self.relative_gpu = dict()
        self.relative_gpu['predicted_ms'] = list()
        self.relative_gpu['start_cpu_ms'] = list()
        self.relative_gpu['done_cpu_ms'] = list()
        self.relative_gpu['done_draw_ms'] = list()
        self.relative_gpu['done_gpu_ms'] = list()
        self.relative_display = dict()
        self.relative_display['predicted_ms'] = list()
        self.relative_display['start_cpu_ms'] = list()
        self.relative_display['done_cpu_ms'] = list()
        self.relative_display['done_draw_ms'] = list()
        self.relative_display['done_gpu_ms'] = list()


def diff_in_ns_to_ms(a, b):
    diff_ns = a - b
    diff_ms = diff_ns / 1000.0 / 1000.0

    return diff_ms

def makeRelative(d, to, f):
    predicted_ms = diff_in_ns_to_ms(f.when_predicted_ns, to)
    start_cpu_ms = diff_in_ns_to_ms(f.when_wait_woke_ns, to)
    done_cpu_ms = diff_in_ns_to_ms(f.when_begin_ns, to)
    done_draw_ms = diff_in_ns_to_ms(f.when_delivered_ns, to)
    done_gpu_ms = diff_in_ns_to_ms(f.when_gpu_done_ns, to)

    d['predicted_ms'].append(predicted_ms)
    d['start_cpu_ms'].append(start_cpu_ms)
    d['done_cpu_ms'].append(done_cpu_ms)
    d['done_draw_ms'].append(done_draw_ms)
    d['done_gpu_ms'].append(done_gpu_ms)

def handleSessionFrame(m, f):
    if f.discarded:
        return

    cpu_ms = diff_in_ns_to_ms(f.when_begin_ns, f.when_wait_woke_ns)
    draw_ms = diff_in_ns_to_ms(f.when_delivered_ns, f.when_begin_ns)
    gpu_ms = diff_in_ns_to_ms(f.when_gpu_done_ns, f.when_delivered_ns)

    makeRelative(m.relative_gpu, f.predicted_gpu_done_time_ns, f)
    makeRelative(m.relative_display, f.predicted_display_time_ns, f)

    m.frame_ids.append(f.frame_id)
    m.absolute['cpu_ms'].append(cpu_ms)
    m.absolute['draw_ms'].append(draw_ms)
    m.absolute['gpu_ms'].append(gpu_ms)

    return


def makeAbsoluteChart(m, width, height):
    colors = bokeh.palettes.Category10[10]
    
    f = bokeh.plotting.figure(title="Absolute", width=width, height=height)
    f.xaxis.axis_label = 'frame_ids'

    for i, key in enumerate(m.absolute):
        value = m.absolute[key]
        f.circle(m.frame_ids, value, legend_label=key, color=colors[i])

    # After to avoid warnings
    f.legend.click_policy = 'hide'

    return f

def makeRelativeChart(m, title, d, width, height):
    colors = bokeh.palettes.Category10[10]

    f = bokeh.plotting.figure(title=title, width=width, height=height)
    f.xaxis.axis_label = 'frame_ids'

    for i, key in enumerate(d):
        value = d[key]
        f.line(m.frame_ids, value, legend_label=key, color=colors[i])

    # After to avoid warnings
    f.legend.click_policy = 'hide'

    return f

def makeCharts(m, width=1000, height=400):
    charts = []
    charts.append([makeAbsoluteChart(m, width, height)]) # Array of Array for vertical spacing.
    charts.append([makeRelativeChart(m, "Relative predicted gpu done time", m.relative_gpu, width, height)])
    charts.append([makeRelativeChart(m, "Relative predicted display time", m.relative_display, width, height)])


    # Make axis locked
    charts[1][0].x_range = charts[0][0].x_range
    charts[2][0].x_range = charts[0][0].x_range

    # Plot and reuse
    return bokeh.plotting.gridplot(charts)


def readBin(file):
    data=None
    try:
        f = open(file, 'rb')
        data = f.read()
        f.close()
    except IOError:
        print("Error")

    r = Record()
    m = Metrics()

    next_pos, pos = 0, 0
    while pos < len(data):
        next_pos, pos = decodeVariant(data, pos)
        r.ParseFromString(data[pos:pos + next_pos])

        which = r.WhichOneof('record')
        match which:
            case 'session_frame':
                handleSessionFrame(m, r.session_frame)
            case 'compositor_frame':
                handleCompositorFrame(m, r.compositor_frame)
            case _:
                print(which)

        pos += next_pos

    return m


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file',
        metavar = 'METRICS_FILE',
        help='File holding metrics data')
    parser.add_argument(
        '--open-plot',
        default=False,
        action="store_true",
        help="If selected, plots will be opened.")
    parser.add_argument(
        '--plot-output-file',
        default=None,
        help="Plots will be outputted to this file.")
    args = parser.parse_args()

    m = readBin(args.file)

    c = makeCharts(m)

    if (args.plot_output_file):
        bokeh.io.output_file(args.plot_output_file)

    if args.open_plot:
        bokeh.io.show(c)
    elif args.plot_output_file:
        bokeh.io.save(c)


#####
# Old stuff
#

def writeMsg(f, msg):
    str = msg.SerializeToString()
    encodeVariant(f.write, len(str), True)
    f.write(str)

def writeBin(file):
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


#####
# Runnable s script
#

if __name__ == '__main__':
    main()
