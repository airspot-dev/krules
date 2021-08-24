# KRules : The Rules overview

![Krules Logo](https://github.com/airspot-dev/krules/blob/feature/docs/.support/krules_ext_logo.png)

in here you can find everything about the KRules Rules, from base to advanced level.

Rulesets and Rules are one of the core concepts of the KRules framework, and in this document they will be throughly explained. 

## What is a Ruleset ?

KRules uses [`Knative`](https://knative.dev) behind the hood, and rules are a way to abstract Knative microservices. In this way you do not need to have advanced Knative knowledge to deploy a serverless environment.

A `Ruleset` is a set of rules, and is used to define the primary entry point for your KRules microservices.

You can define a ruleset with the help of the  [***KRules CLI (TODO)***](./TODO).

``` bash
krules scaffold TODO
```

After your ruleset is created you can then add rules inside it to develop the logic of your application.

# What is a Rule ?

A `Rule` is one of the core concepts of the KRules framework. It is an object which performs the following actions:

- Perform reactive updates and provide statefulness thanks to a context called [`Subject`](./subjects.md).
- Produce and consume [cloud events](https://cloudevents.io) coming from the Knative eventing.

## Anatomy of a Rule

A rule is composed by the following elements:

- `rulename`: The name of the rule, must be unique.
- `subscribe_to`: The array of cloudevents the rule is set to react to. Determines the reactive property of the rules.
- `ruledata`: An object containing the following data:
  - `filters`: They are described in the section below, but they can be summarized as a way to filter rules execution.
  - `processing`: They are composed by a set of `RuleFunction` instances and by being compose they determine what the rule will do during its execution.

## What are filters ?

Filters are used to filter incoming cloud events to the rules, to execute the RuleFunctions only when those filters are passed.

## How to add a filter to a rule ?

You can add a filter to a rule by using the `filters` property of the rule object. A very simple example is the one below:

``` python
from krules_core.arg_processors import SubjectNameMatch

rulesdata = [
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            filters: [
                SubjectNameMatch("a_string"),
            ],
            processing: [
                # add your rule functions
            ],
        },
    },
]
```

There is a number of available filters, please refer to the [***API Reference (TODO)***](./TODO)

## Defining rules

To achieve their goals, rules must be defined and implemented. The standard way to do that is through the usage of ***`rulesdata` variable*** or **`RuleFactory` class**.

Let's say we define the following Rule function (don't worry, we will come back to this later)

``` python
from krules_core.base_functions import RuleFunctionBase

class Print(RuleFunctionBase):
    def execute(self, text):
        print(text)
```

you can add a rule to the ruleset like this:
``` python
rulesdata=[
    # In here I am adding a rule to the ruleset.
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                Print("Hello World!"),
            ],
        }
    },
]
```

or like this (Using `RuleFactory`):

``` python
from krules_core.core import RuleFactory

RuleFactory.create({
    "test",
    subscribe_to="...",
    data={
        processing: [
            Print("Hello World!"),
        ],
    },
})
```

# What is a Rule Function?

You have one principal way to define a Rule. And this way is through Rule Functions.

A Rule Function is a python class which extends `RuleFunctionBase` and implements the methods defined below:

``` python 
class MyRuleFunction(RuleFunctionBase):
    """
    The RuleFunction is an example Rule Function.

    Methods:
    ----------
    execute():
        Performs the logic of the rule function.
    """

    def execute(self, *args, **kwargs):
        """
        Performs the logic of the rule function.
        """
        pass
```

Let's dive into an example implementation right away!

## The Print RuleFunction, an example to rule them all

The `Print` RuleFunction can be used to log a text upon receipt of a certain event.

You can define it like the following class:

``` python
from krules_core.base_functions import RuleFunctionBase

class Print(RuleFunctionBase):
    """
    The Print RuleFunction is an Argument Processor which logs the text, passed as parameter.

    Methods:
    ----------
    execute():
        Performs the logic of the argument processor.
    """

    def execute(self, text):
        """
        Performs the logic of the argument processor, using the provided text.

        Parameters
        ----------
        text : str
            The text to print
        """
        print(text)
```

and while you actually add it to a rule, the code should be similar to this

``` python
from krules_core.base_functions import RuleFunctionBase

class Print(RuleFunctionBase):
    def execute(self, text):
        print(text)

# ...
rulesdata=[
    # In here I am adding a rule to the ruleset.
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                Print("Hello World!"),
            ],
        },
    },
]
```

In this example, at startup, there will be created a `Print` Rule function instance which logs a pre-defined message; however a reactive system must react to state system changes, therefore it is logical to assume that even the parameters of its functions can change with it by accessing information at runtime during the execution of the Rule itself.

Take this new implementation as example, which allows to log a message received in the payload of the event that has just been received.

``` python
from krules_core.base_functions import RuleFunctionBase

class PrintMessageFromPayload(RuleFunctionBase):
    """
    PrintMessageFromPayload prints the 'message' field from an incoming payload.
    
    Attributes:
    ----------
    payload (dict):
        The payload passed to the RuleFunction, must have a 'message' field.

    Methods:
    ----------
    execute():
        Performs the logic of the argument processor.
    """

    def execute(self):
        """
        Performs the logic of the argument processor, using the payload's 'message' field.
        """
        print(self.payload["message"])
```

and again, let's see its usage in a Rule

``` python 
from krules_core.base_functions import RuleFunctionBase

class PrintMessageFromPayload(RuleFunctionBase):
    def execute(self):
        print(self.payload["message"])

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                PrintMessageFromPayload(),
            ],
        }
    },
]
```

## What's next ?

If you think you understood everything perfectly, you are ready to move to the next topic: [***The Argument Processors***](./argument-processors.md).