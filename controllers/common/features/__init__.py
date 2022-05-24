
def update_features_labels(configuration, service):
    if "labels" not in service['metadata']:
        service['metadata']['labels'] = {}

    labels = service['metadata']['labels']
    features = configuration.get("spec", {}).get("extensions", {}).get("features", {})

    # clean previous
    # search for <feature>/...
    to_delete = []
    for feature_k in features:
        for label in labels:
            if label.startswith(f"{feature_k}/"):
                to_delete.append(label)
    for label in to_delete:
        del labels[label]

    # add features labels
    new_labels = {}
    for feature_k in features:
        for feature in features[feature_k]:
            new_labels[f"features.{feature_k}/{feature}"] = "enabled"  # features[feature_k][feature]

    labels.update(new_labels)

    return new_labels
