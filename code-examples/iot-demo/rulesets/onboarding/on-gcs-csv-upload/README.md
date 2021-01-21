# on-gcs-csv-upload

Responds to addition of a new csv file in the GCS bucket and parse it to generate a device-data event with the 
new device subject.

If csv file is malformed raise an error. This ruleset responds also to the error event to delete the corrupted file 
from GCS bucket   