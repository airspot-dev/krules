# KRules : The Subjects overview

![Krules Logo](https://github.com/airspot-dev/krules/blob/feature/docs/.support/krules_ext_logo.png)

in here you can find everything about the KRules subjects, including what they are and how they are connected with [***Rules and Rulesets***](./rules.md), use and extend their properties to meet your custom needs.

The Subjects are one of the core concepts of the KRules framework. You can think of them as the context of a [**Rule**](./rules.md).

## What is a subject?

A subject is an object composed of reactive properties, which can be leveraged to achieve the statefulness of your system.

When a property in a subject is changed in some ways, a cloud event is emitted, making possible for rules to catch the event and process it in a reactive way.

There are also some properties called extended properties, which ... TODO

## How can I use a subject in the proper way ?

To use subjects correctly you need to:
1. Setup the changes you want correctly.
2. Catch the `subject-property-changed` cloud events.

Here is how to do it.

### Setting a subject reactive property 

To trigger a property change, you can use the `SetSubjectProperty` rule function:

``` python
from krules_core.arg_processors import SetSubjectProperty

# ...

rulesdata=[
    {
        processing: [
            SetSubjectProperty("proc_time", datetime.now),
        ],
    },
]
```

Easy as that, in this example you are setting a property called `proc_time` in the subject, emitting
a `subject-property-changed` event which needs to be catched and handled somewhere (hopefully).

### Reacting to subject property changes

If you need to listen to the change events from a rule you can use the `OnSubjectPropertyChanged` filter (if you need an overview about the filters, you can find it [***HERE***](./filters.md)).

``` python
from krules_core.arg_processors import OnSubjectPropertyChanged

# ...

ruledata={
    filters: [
        OnSubjectPropertyChanged(
            "proc_time",
        ),
    ],
    processing: [
        Print(lambda payload: payload["proc_time"]),
    ],
}
```

In this way the event will be handled by printing the `proc_time` when it changes. This is just an example of what you can do with the framework.

### Filtering event changes

You can also add more filter to event changes. Let's take the following example:

``` python
from random import randint
from krules_core.arg_processors import SetSubjectProperty, OnSubjectPropertyChanged

# ...

rulesdata=[
    {
        processing: [
            # here we are simulating to receive some temperature data from an
            # iot device, for example.
            SetSubjectProperty("temperature", randint(-20, +20)),
        ],
    },
    {
        filters: [
            OnSubjectPropertyChanged(
                "temperature",
                old_value=lambda old_value,value: value <= 0,
            ),
        ],
        processing: [
            SetSubjectProperty(
                "status",
                "COLD",
            ),
        ],
    },
    {
        filters: [
            OnSubjectPropertyChanged(
                "temperature",
                old_value=lambda old_value,value: value > 0,
            ),
        ],
        processing: [
            SetSubjectProperty(
                "status",
                "HOT",
            ),
        ],
    },
    {
        filters: [
            OnSubjectPropertyChanged(
                "status"
            ),
        ],
        processing: [
            Print(lambda payload: payload["status"])
        ]
    }
]
```

In the provided example, we set a new property `status` using the property changes from the `temperature` property. This is particularly useful because we can react to `status` changes as well, and print them (as an example, but we can do a lot more).