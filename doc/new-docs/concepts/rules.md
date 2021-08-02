# KRules : The Rules overview

in here you can find everything about the KRules Rules, from base to advanced level.

# What is a Rule ?

# What is a Filter ? 

# What is a Rule Function?

## The Print RuleFunction, an example to rule them all

The `Print` RuleFunction can be used to log a text upon receipt of a certain event.

You can define it like the following class:

``` python
"""
The Print RuleFunction is an Argument Processor which
logs the text, passed as parameter.
"""
class Print(RuleFunctionBase):
    """
    The execute method will perform the logic
    of the argument processor.
    """
    def execute(self, text):
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
            Print("Hello World!")
        ]
    }
]
```

In this example, at startup, there will be created a `Print` Rule function instance which logs a pre-defined message; however a reactive system must react to state system changes, therefore it is logical to assume that even the parameters of its functions can change with it by accessing information at runtime during the execution of the Rule itself.

Take this new implementation as example, which allows to log a message received in the payload of the event that has just been received.

``` python
"""
PrintMessageFromPayload prints the "message" field from
an incoming payload.
"""
class PrintMessageFromPayload(RuleFunctionBase):
    """
    The execute method will perform the logic
    of the argument processor.
    """
    def execute(self):
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
            PrintMessageFromPayload()
        ]
    }
]
```

## What's next ?

If you think you understood everything perfectly, you are ready to move to the next topic: [***The Argument Processors***](./argument-processors.md)