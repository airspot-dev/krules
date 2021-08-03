# KRules : The Rules overview

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

- Perform reactive updates and provide statefulness thanks to a context called [`Subject`](./subjects.md)

# What is a Filter ? 

# What is a Rule Function?

## The Print RuleFunction, an example to rule them all

The `Print` RuleFunction can be used to log a text upon receipt of a certain event.

You can define it like the following class:

``` python
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
class Print(RuleFunctionBase):
    def execute(self, text):
        print(text)

# ...
rulesdata=[
    # In here I am adding a rule to the ruleset.
    {
        processing: [
            Print("Hello World!"),
        ],
    },
]
```

In this example, at startup, there will be created a `Print` Rule function instance which logs a pre-defined message; however a reactive system must react to state system changes, therefore it is logical to assume that even the parameters of its functions can change with it by accessing information at runtime during the execution of the Rule itself.

Take this new implementation as example, which allows to log a message received in the payload of the event that has just been received.

``` python
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
class PrintMessageFromPayload(RuleFunctionBase):
    def execute(self):
        print(self.payload["message"])

# ...

rulesdata=[
    {
        processing: [
            PrintMessageFromPayload(),
        ],
    },
]
```

## What's next ?

If you think you understood everything perfectly, you are ready to move to the next topic: [***The Argument Processors***](./argument-processors.md).