import json


def update_features_labels(configuration, service):
    if "labels" not in service['metadata']:
        service['metadata']['labels'] = {}

    labels = service['metadata']['labels']
    features = json.loads(configuration.get("metadata", {}).get("annotations", {}).get("krules.dev/features", "[]"))
    
    if not len(features):
        return {}

    # clean previous
    for label in labels:
        if label.startswith(f"features.krules.dev/"):
            labels[label] = None

    # add features labels
    new_labels = {}
    for feature in features:
        new_labels[f"features.krules.dev/{feature}"] = "enabled"  # features[feature_k][feature]

    labels.update(new_labels)

    return new_labels
