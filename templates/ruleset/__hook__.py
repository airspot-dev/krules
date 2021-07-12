"""
# Create a new ruleset

The following environment variables are set in **.env** file

- **APP_NAME**: It'll be the name of the ruleset service. If not set defaults to destination directory name
- **IMAGE_NAME**: Name of the image that will be built. If not set defaults to ${PROJECT_NAME}-${APP_NAME}
- **SERVICE_API**: If set to **base** (default) a standard kubernetes deployment and service (ClusterIP) will be created.
  If set to **knative** a knative service will be created with cluster-local visibility
"""