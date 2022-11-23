# Monado Metrics Tools

<!--
Copyright 2022, Collabora, Ltd. and the Monado contributors
SPDX-License-Identifier: BSL-1.0
-->

To run tools make sure to install python protobuf and bokeh.

First build the protobuf python file with make.

```bash
make
```

Then run the cmd.py file and give it the protobuf file containing Monado metrics.

```bash
./cmd.py --open-plot /path/to/file.protobuf
```
