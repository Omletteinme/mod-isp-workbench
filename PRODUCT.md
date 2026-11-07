# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Researchers and developers evaluating image signal processing experiments on a local machine.

## Product Purpose

A local workbench for processing rendered RGB images and Bayer sensor inputs through available classical, learned, and hybrid restoration paths, then inspecting outputs and run measurements.

## Positioning

The workbench exposes the actual local processing paths and their measured outputs, including optional aligned-reference metrics, rather than presenting unverified benchmark claims.

## Operating Context

Users launch a local Flask server, choose or drop an image, optionally attach a matching reference, select Human or Machine vision output profile, process the image, switch between available ISP paths, inspect results and download an output. Inputs are not sent to a hosted service.

## Capabilities and Constraints

Supports rendered RGB (JPEG, PNG, WebP, TIFF) and supported camera RAW / normalized RGGB NPY Bayer inputs, subject to 30 MB upload and 16 MP processing limits (RAW/NPY over the limit are rejected). RGB and Bayer use distinct model paths. Available paths depend on locally present checkpoints. Reference metrics require a dimension-matched aligned reference. Displayed memory excludes native and accelerator allocations. This is an experimental implementation and has not met projected blueprint quality targets; results from small scene-separated samples do not establish generalization. No mobile NPU performance is established.

## Brand Commitments

The user supplied a reference image with a crisp editorial interface, restrained blue accent, precise grid lines, and compact technical labels. Adapt this visual reference to the actual workbench.

## Evidence on Hand

Implementation and checkpoint details in README.md, app.py, and models/*.json; local processor availability via /api/status; per-run outputs and metrics via /api/process. No approved testimonials or general-purpose performance claims are supplied.

## Product Principles

- Keep every displayed result tied to actual local execution.
- Make the selected processing path and input domain clear.
- Preserve the distinction between rendered RGB and Bayer sensor data.
- Make experimental limits visible where they affect interpretation.
