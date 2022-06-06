import json


def update_features_labels(configuration, service):
    if "labels" not in service['metadata']:
        service['metadata']['labels'] = {}

    labels = service['metadata']['labels']
    features = json.loads(configuration.get("metadata", {}).get("annotations", {}).get("krules.dev/features", "{}"))

    # clean previous
    for label in labels:
        if label.startswith(f"features."):
            labels[label] = None

    # add features labels
    new_labels = {}
    for feature_k in features:
        for feature in features[feature_k]:
            new_labels[f"features.{feature_k}/{feature}"] = "enabled"  # features[feature_k][feature]

    labels.update(new_labels)

    return new_labels
