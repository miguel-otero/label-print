#!/bin/bash

# ----------------------------------------------------------------------------
# This script updates the Google Cloud Storage bucket with the latest version
# of the app, for production environment deployment.
# ----------------------------------------------------------------------------

# sh ./scripts/gcp_login.sh

zip -r deploy.zip \
  app scripts docker README.md .gitignore docker-compose.yaml conn/ \
  -x "*/node_modules/*" \
  -x "*/__pycache__/*" \
  -x "*/update_zip.sh"

gsutil cp deploy.zip gs://label-print-cv/deploy.zip
rm deploy.zip
