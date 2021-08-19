# KRules : The Filters overview

![Krules Logo](https://github.com/airspot-dev/krules/blob/feature/docs/.support/krules_ext_logo.png)

in here you can find everything about the KRules Filters, from base to advanced level.

## What are filters ?

Filters are used to filter incoming cloud events to the rules, to execute the RuleFunctions only when those filters are passed.

## How to add a filter to a rule ?

You can add a filter to a rule by using the `filters` property of the rule object. A very simple example is the one below:

``` python
from krules_core.arg_processors import SubjectNameMatch

ruleset = [
    {
        filters: [
            SubjectNameMatch("a_string")
        ],
        processing: [
            # add your rule functions
        ]
    }
]
```

There is a number of available filters, please refer to the [***API Reference (TODO)***](./TODO)