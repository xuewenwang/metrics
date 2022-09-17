# Copyright 2022, Collabora, Ltd.
# SPDX-License-Identifier: BSL-1.0


PROTO=proto/monado_metrics.proto
OUT_PB=out/monado_metrics.pb
OUT_PY=src/proto/monado_metrics_pb2.py

all: build

build: $(OUT_PY)

run: build
	@echo " :: RUN cmd.py"
	@./cmd.py


gen-nanopb: $(OUT_PB)
	@echo " :: NANOPB"
	@../nanopb/generator/nanopb_generator.py -D out  --strip-path out/monado_metrics.pb

gen-protobuf-c: $(PROTO)
	@echo " :: PROTOC-C"
	@protoc-c  --proto_path=proto/   proto/monado_metrics.proto --c_out=out


$(OUT_PY): $(PROTO)
	@echo " :: PROTOC $@"
	@mkdir -p $(dir $@)
	@protoc --proto_path=proto/ --python_out=src/proto $(PROTO)

$(OUT_PB): $(PROTO)
	@echo " :: PROTOC $@"
	@mkdir -p $(dir $@)
	@protoc -o $(OUT_PB) $(PROTO)


.PHONY: all build run gen-nanopb gen-protobuf-c
