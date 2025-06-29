#!/bin/bash

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "❌ Usage: $0 <artifact_name> [project_name]"
  exit 1
fi

ARTIFACT_NAME="$1"
PROJECT_NAME="${2:-artifactory}"  # Default to "artifactory" if $2 is not provided
TOKEN="${TOKEN:?You must set the TOKEN environment variable}"
JFROG_URL="https://psazuse.jfrog.io"
BUILD_REPO="${PROJECT_NAME}-build-info"

# Step 1: Search for build.name and build.number using AQL
AQL_QUERY=$(cat <<EOF
items.find({
  "name": "${ARTIFACT_NAME}"
}).include("property", "created")
EOF
)

ITEMS_RESPONSE=$(curl -s -X POST "$JFROG_URL/artifactory/api/search/aql" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/plain" \
  -d "$AQL_QUERY")

# Step 2: Extract the most recent build (based on creation date)
BUILD_INFO_FROM_AQL=$(echo "$ITEMS_RESPONSE" | jq -r '
  .results
  | sort_by(.created) 
  | reverse
  | .[] 
  | {
      build_name: (.properties[]? | select(.key == "build.name") | .value),
      build_number: (.properties[]? | select(.key == "build.number") | .value)
    }
  | select(.build_name and .build_number)
  | @base64' | head -n1)

if [[ -z "$BUILD_INFO_FROM_AQL" ]]; then
  echo "❌ Could not find build.name or build.number for artifact: $ARTIFACT_NAME"
  exit 1
fi

# Helper function to decode base64 and extract values
decode() {
  echo "$1" | base64 --decode | jq -r "$2"
}

BUILD_NAME=$(decode "$BUILD_INFO_FROM_AQL" '.build_name')
BUILD_NUMBER=$(decode "$BUILD_INFO_FROM_AQL" '.build_number')

# Step 3: Fetch build details from the build API
BUILD_INFO=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$JFROG_URL/artifactory/api/build/${BUILD_NAME}/${BUILD_NUMBER}?buildRepo=${BUILD_REPO}")

# Step 4: Extract specific buildInfo.env properties
CI_PROJECT_NAME=$(echo "$BUILD_INFO" | jq -r '.buildInfo.properties["buildInfo.env.CI_PROJECT_NAME"] // empty')
CI_COMMIT_BRANCH=$(echo "$BUILD_INFO" | jq -r '.buildInfo.properties["buildInfo.env.CI_COMMIT_REF_SLUG"] // empty')

# Step 5: Output all extracted data as clean JSON
jq -n \
  --arg artifact "$ARTIFACT_NAME" \
  --arg build_name "$BUILD_NAME" \
  --arg build_number "$BUILD_NUMBER" \
  --arg CI_PROJECT_NAME "$CI_PROJECT_NAME" \
  --arg CI_COMMIT_BRANCH "$CI_COMMIT_BRANCH" \
  '{
    artifact: $artifact,
    build_name: $build_name,
    build_number: $build_number,
    CI_PROJECT_NAME: $CI_PROJECT_NAME,
    CI_COMMIT_BRANCH: $CI_COMMIT_BRANCH
  }'