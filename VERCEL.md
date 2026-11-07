# Vercel deployment

The Vercel project serves the MOD-ISP interface as a static project page. The full image-processing workbench remains a local or Docker application.

## Why inference is not hosted on Vercel

- Flask is deployed as one Vercel Function, and the current Python runtime bundle limit is 500 MB. The available PyTorch package in the project's local environment occupies 626 MB before NumPy, SciPy, image libraries, and application code.
- Vercel Functions have a 4.5 MB request and response body limit. The local app accepts 30 MB and returns the input plus three base64-encoded image outputs; a recorded 16 MP comparison response was 13.7 MB.
- The local interface promises that image processing stays on the user's machine. A hosted inference path would change where private image data is processed.

The static Vercel page points visitors to the repository's setup instructions and does not accept uploads. To run inference, follow the [local setup](README.md#quick-start) or [Docker setup](README.md#docker-runtime).

## Project configuration

`vercel.json` builds a static output directory from `templates/index.html` and `static/` using `scripts/build_vercel_site.py`. The `.vercelignore` file excludes local datasets, virtual environments, and scratch files.

The current Vercel project is not connected to GitHub because this Vercel account does not have a GitHub Login Connection. Pushes to GitHub therefore do not deploy automatically. After updating the interface, run `scripts/deploy_vercel_static.sh` with the Vercel CLI authenticated to the project team. The script rebuilds `dist/` and uploads only those static files, without Git commit metadata or the Python training dependencies.

References: [Vercel Flask](https://vercel.com/docs/frameworks/backend/flask), [Python runtime bundle limits](https://vercel.com/docs/functions/runtimes/python), and [Vercel Function limits](https://vercel.com/docs/functions/limitations).
