# KRules : The Subjects overview

in here you can find everything about the KRules subjects, including what they are and how they are connected with [***Rules and Rulesets***](./rules.md), use and extend their properties to meet your custom needs.

The Subjects are one of the core concepts of the KRules framework. You can think of them as the context of a [**Rule**](./rules.md).

## What is a subject?

A subject is an object composed of reactive properties, which can be leveraged to achieve the statefulness of your system.

When a property in a subject is changed in some ways, a cloud event is emitted, making possible for rules to catch the event and process it in a reactive way.

There are also some properties called extended properties, which ... TODO

## How can I use a subject in the proper way ?

To trigger a property change, you can use the `SetSubjectProperty` rule function:

``` python

```

While if you need to listen to the change events from a rule you can use the `OnSubjectPropertyChanged` filter (if you need an overview about the filters, you can find it [***HERE***](./filters.md)).

``` python

```