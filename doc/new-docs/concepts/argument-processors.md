# KRules : The Argument Processors overview

in here you can find everything about the KRules argument processors, including how to create, use and extend their functionality to meet you custom needs.

The Argument Processors are one of the core concepts of the KRules framework. You can think of them as the processing units of a [**Rule**](./rules.md).

Be aware that you need to fully understand how the Rules work before diving into the Argument Processors.
   
## The Print Rule function example and why does it matter

If you saw the [`Print` RuleFunction example in the rules chapter](./rules.md), you have seen it's possible to extract a field from the payload and log it.

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

However, it is possible to achieve the same effect with the generic function defined in our first try:

``` python
class Print(RuleFunctionBase):
    def execute(self, text):
        print(text)

# ...

rulesdata=[
    {
        processing: [
            Print(lambda payload: payload["message"])
        ]
    }
]
```

This is possible thanks to the **Argument Processors**.

# What is an Argument Processor ?

An argument processor is a class that implement 2 simple methods:

- **interested_in(arg)** : A boolean method which, receiving an argument, it checks whether if it meets the requirements for it to be processed by the argument processor;
- **process(instance)** : It is the method where the argument conversion actually take place starting from the instance of the rule that is being currently executed allowing, for example, access to the status information at runtime.

At the startup, each argument of each RuleFunction is examined in order to identify which is the argument processor interested in argument and consequently instantiate it.
If no argument processor declares itself interested, the argument will be treated as it is without being processed at runtime.
