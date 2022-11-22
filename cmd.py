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

import pandas as pd

import bokeh.io
import bokeh.layouts
import bokeh.models
import bokeh.palettes
import bokeh.plotting


class VersionError(Exception):
    """Version mismatch"""

    def __init__(self, major, minor):
        self.major = major
        self.minor = minor
        super().__init__("Does not support version {}.{} files!".format(major, minor))

@dataclass
class SystemMetrics:
    """
    A collection of metrics for the system.
    """

    frame_ids: list
    absolute: dict[str, list[float]]
    predicted_present: dict[str, dict[float]]
    absolute_gpu_only: dict[str, list[float]]

    def __init__(self):
        self.frame_ids = list()
        self.absolute = dict()
        self.absolute['cpu_ms'] = list()
        self.absolute['draw_ms'] = list()
        self.absolute['gpu_ms'] = list()
        #self.absolute['submit_ms'] = list()
        self.predicted_present = dict()
        self.predicted_present['predicted_ms'] = list()
        self.predicted_present['start_cpu_ms'] = list()
        self.predicted_present['done_cpu_ms'] = list()
        self.predicted_present['submitted_ms'] = list()
        self.predicted_present['gpu_ms'] = list()
        self.predicted_present['present_ms'] = list()
        self.absolute_gpu_only = dict()
        self.absolute_gpu_only['gpu_ms'] = list()


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
        self.system = SystemMetrics()
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

####
# Version
#

def handleVersion(m, v):
    if (v.major != 1):
        raise VersionError(v.major, v.minor)

####
# Used
#

def handleUsed(m, f):
    return


####
# System GPU Info
#

def handleSystemGpuInfo(m, f):
    gpu_ms = diff_in_ns_to_ms(f.gpu_end_ns, f.gpu_start_ns)

    #m.system.absolute['gpu_ms'].append(gpu_ms)
    m.system.absolute_gpu_only['gpu_ms'].append(gpu_ms)


####
# System Present Info
#

def handleSystemPresentInfo(m, f):
    # Synthesized value
    when_gpu_done_ns = f.actual_present_time_ns - f.present_margin_ns

    # Frame ids
    m.system.frame_ids.append(f.frame_id)

    # Absoulte chart
    cpu_ms = diff_in_ns_to_ms(f.when_began_ns, f.when_woke_ns)
    draw_ms = diff_in_ns_to_ms(f.when_submitted_ns, f.when_began_ns)
    gpu_ms = diff_in_ns_to_ms(when_gpu_done_ns, f.when_submitted_ns)

    m.system.absolute['cpu_ms'].append(cpu_ms)
    m.system.absolute['draw_ms'].append(draw_ms)
    m.system.absolute['gpu_ms'].append(gpu_ms)

    # Relative chart
    predicted_ms = diff_in_ns_to_ms(f.when_predict_ns, f.desired_present_time_ns)
    start_cpu_ms = diff_in_ns_to_ms(f.when_woke_ns, f.desired_present_time_ns)
    done_cpu_ms = diff_in_ns_to_ms(f.when_began_ns, f.desired_present_time_ns)
    submitted_ms = diff_in_ns_to_ms(f.when_submitted_ns, f.desired_present_time_ns)
    gpu_ms = diff_in_ns_to_ms(when_gpu_done_ns, f.desired_present_time_ns)
    present_ms = diff_in_ns_to_ms(f.actual_present_time_ns, f.desired_present_time_ns)

    m.system.predicted_present['predicted_ms'].append(predicted_ms)
    m.system.predicted_present['start_cpu_ms'].append(start_cpu_ms)
    m.system.predicted_present['done_cpu_ms'].append(done_cpu_ms)
    m.system.predicted_present['submitted_ms'].append(submitted_ms)
    m.system.predicted_present['gpu_ms'].append(gpu_ms)
    m.system.predicted_present['present_ms'].append(present_ms)


####
# System frame
#

def handleSystemFrame(m, f):
    return


####
# Session frame
#

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


####
# Chart functions
#

def makeBoxChart(d):
    cats = list(d.keys())
    df = pd.DataFrame(d)
    q1 = df.quantile(q = 0.25)
    q2 = df.quantile(q = 0.5)
    q3 = df.quantile(q = 0.75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    lower = q1 - 1.5 * iqr

    outx = list()
    outy = list()
    def outlier(group):
        cat = group.name
        listOfOutliersPerColumn = group[(group > upper.loc[cat]) | (group < lower.loc[cat])]
        for v in listOfOutliersPerColumn:
            outx.append(cat)
            outy.append(v)
    df.apply(outlier)

    f = bokeh.plotting.figure(background_fill_color = "#efefef", x_range = cats)

    # limit upper and lower to values
    for key in cats:
        minV = df[key].min()
        maxV = df[key].max()
        if lower[key] < minV:
            lower[key] = minV
        if upper[key] > maxV:
            upper[key] = maxV

    # stems
    f.segment(cats, upper, cats, q3, line_color = "black")
    f.segment(cats, lower, cats, q1, line_color = "black")

    # boxes
    f.vbar(cats, 0.7, q2, q3, fill_color = "#E08E79", line_color = "black")
    f.vbar(cats, 0.7, q1, q2, fill_color = "#3B8686", line_color = "black")

    # whiskers (almost-0 height rects simpler than segments)
    f.rect(cats, lower, 0.2, 0.01, line_color = "black")
    f.rect(cats, upper, 0.2, 0.01, line_color = "black")

    f.circle(outx, outy, size=6, color="#F38630", fill_alpha=0.6)

    f.xgrid.grid_line_color = None
    f.grid.grid_line_width = 2
    f.xaxis.major_label_text_font_size = "16px"

    return f


def makeAbsolteBoxChart(m, charts):
    d = dict()
    for key in m.absolute.keys():
        nkey = 'session_' + key
        d[nkey] = m.absolute[key]
    charts.append([makeBoxChart(d)])

    d = dict()
    for key in m.system.absolute.keys():
        nkey = 'system_' + key
        d[nkey] = m.system.absolute[key]
    charts.append([makeBoxChart(d)])


def makeAbsoluteChart(frame_ids, d, width, height):
    colors = bokeh.palettes.Category10[10]
    
    f = bokeh.plotting.figure(title="Absolute", width=width, height=height)
    f.xaxis.axis_label = 'frame_ids'

    for i, key in enumerate(d):
        value = d[key]
        f.circle(frame_ids, value, legend_label=key, color=colors[i])

    # After to avoid warnings
    f.legend.click_policy = 'hide'

    return f


def makeRelativeChart(frame_ids, d, title, width, height):
    colors = bokeh.palettes.Category10[10]

    f = bokeh.plotting.figure(title=title, width=width, height=height)
    f.xaxis.axis_label = 'frame_ids'

    for i, key in enumerate(d):
        value = d[key]
        f.line(frame_ids, value, legend_label=key, color=colors[i])

    # After to avoid warnings
    f.legend.click_policy = 'hide'

    return f


def makeSessionCharts(m, charts, width=1000, height=400):
    first = len(charts)
    charts.append([makeAbsoluteChart(m.frame_ids, m.absolute, width, height)]) # Array of Array for vertical spacing.
    charts.append([makeRelativeChart(m.frame_ids, m.relative_gpu, "Relative predicted gpu done time", width, height)])
    charts.append([makeRelativeChart(m.frame_ids, m.relative_display, "Relative predicted display time", width, height)])

    # Make axis locked
    charts[first + 1][0].x_range = charts[first][0].x_range
    charts[first + 2][0].x_range = charts[first][0].x_range


def makeSystemCharts(m, charts, width=1000, height=400):
    title = "Relative predicted present time"
    frame_ids = m.system.frame_ids

    first = len(charts)
    charts.append([makeAbsoluteChart(frame_ids, m.system.absolute, width, height)]) # Array of Array for vertical spacing.
    charts.append([makeRelativeChart(frame_ids, m.system.predicted_present, title, width, height)])

    # Make axis locked
    charts[first + 1][0].x_range = charts[first][0].x_range


def makeCharts(m):
    charts = []

    makeAbsolteBoxChart(m, charts)
    makeSessionCharts(m, charts)
    makeSystemCharts(m, charts)

    # Plot and reuse
    return bokeh.plotting.gridplot(charts)


####
# File reading
#

def readRecord(data, pos, next_pos, r):
    if pos < len(data):
        next_pos, pos = decodeVariant(data, pos)
        r.ParseFromString(data[pos:pos + next_pos])
        pos += next_pos
    return pos, next_pos

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

    # Needed during reading.
    next_pos, pos = 0, 0

    # Grab the first version record.
    if pos < len(data):
        pos, next_pos = readRecord(data, pos, next_pos, r)

        if r.WhichOneof('record') != 'version':
            raise Exception("First record not version tag")

        handleVersion(m, r.version)

    # Looping for all other records.
    while pos < len(data):
        pos, next_pos = readRecord(data, pos, next_pos, r)

        which = r.WhichOneof('record')
        match which:
            case 'version':
                raise Exception("Multiple version tags")
            case 'session_frame':
                handleSessionFrame(m, r.session_frame)
            case 'used':
                handleUsed(m, r.used)
            case 'system_frame':
                handleSystemFrame(m, r.system_frame)
            case 'system_gpu_info':
                handleSystemGpuInfo(m, r.system_gpu_info)
            case 'system_present_info':
                handleSystemPresentInfo(m, r.system_present_info)
            case _:
                print(which)

    return m


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file',
        metavar = 'METRICS_FILE',
        help='File holding metrics data.')
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
