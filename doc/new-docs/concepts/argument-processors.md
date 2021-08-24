# KRules : The Argument Processors overview

![Krules Logo](https://github.com/airspot-dev/krules/blob/feature/docs/.support/krules_ext_logo.png)

in here you can find everything about the KRules argument processors, including how to create, use and extend their functionality to meet you custom needs.

The Argument Processors are one of the core concepts of the KRules framework. You can think of them as the processing units of a [**Rule**](./rules.md).

> Be aware that you need to fully understand how the Rules work before diving into the Argument Processors.
   
## The Print Rule function example and why does it matter

If you saw the [`Print` RuleFunction example in the rules chapter](./rules.md), you have seen it's possible to extract a field from the payload and log it.

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
        },
    },
]
```

However, it is possible to achieve the same effect with the generic function defined in our first try:

``` python
from krules_core.base_functions import RuleFunctionBase

class Print(RuleFunctionBase):
    def execute(self, text):
        print(text)

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                Print(lambda payload: payload["message"]),
            ],
        },
    },
]
```

This is possible thanks to the **Argument Processors**.

# What is an Argument Processor ?

An argument processor is a class that implement 2 simple methods:

``` python
from krules_core.arg_processors import BaseArgProcessor

class MyArgumentProcessor(BaseArgProcessor):
    """
    MyArgumentProcessor is an example implementation of a KRules Argument Processor.
    """

    @staticmethod
    def interested_in(arg):
        """
        Checks whether if the passed arg meets the requirements for it to be processed.

        Parameters
        ----------
        arg (str):
            The argument that needs to be processed.

        Returns
        ----------
        is_interested_in (bool): True if the argument should be processed, False otherwise.
        """
        # ...

    def process(instance):
        """
        Performs the actual argument processing, allowing to access the status information at runtime
        and manipulate the argument and its attributes. You can use it to manipulate the payload
        before the final processing or set subject properties, etc...
        Refer to the Subjects documentation to know more.

        Parameters
        ----------
        instance (dict):
            The argument instance to process. Has a 'payload' attribute.
        """
        # ...
```

At the startup, each argument of each RuleFunction is matched with its argument processor and the argument processor instance, which is created subsequently.
If no argument processor declares itself interested, the argument will be treated as it is without being processed at runtime.

## Available core Argument Processors 

The available argument processors are defined in the module `krules_core.arg_processors` and are defined in the following sections.

### The `SimpleCallableArgProcessor` type

It allows to use a simple function as parameter that will be invoked without providing further parameters. An example of this is `SetSubjectProperty`.

``` python
from krules_core.base_functions import SetSubjectProperty

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                SetSubjectProperty("proc_time", datetime.now),
            ],
        },
    },
]
```

### `CallableWithSelfArgProcessor`

It allows to use a function to which the running RuleFunction instance is passed so that you can access current status information such as the payload or subject. A function, to be eligible to be wrapped to this argument processor, must have only one argument called **self**.

``` python
from krules_core.base_functions import PyCall

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                PyCall(requests.get, args=lambda self: (
                    "http://server.address/{}?attr={}".format(
                        str(self.subject),
                        self.payload["req_attr"],
                    ),
                ),
            ],
        },
    },
]
```

> **WARNING**:
> 
> As the next 2 argument processors, the parameter name is discriminating and not optional.
> 
> The following implementation will not be called correctly, as the lambda parameter name is not `self` but `s`, so pay extra care.

``` python
from krules_core.base_functions import PyCall

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                PyCall(requests.get, args=lambda s: ( # s is wrong parameter name, will fail.
                    "http://server.address/{}?attr={}".format(
                        str(s.subject),
                        s.payload["req_attr"],
                    ),
                ),
            ],
        },
    },
]
```

By defining `PyCall` in this erroneous way **the args parameter will not be processed as `CallableWithSelf` objects and will error.**

### CallableWithPayloadArgProcessor and CallableWithSubjectArgProcessor

Following the concept of the `CallableWithSelfArgProcessor`, 2 other argument processors have been implemented which, however, instead of receiving the entire state, focus only on 2 parts of it, respectively the payload and the subject.

The `CallableWithPayloadArgProcessor` types accept a payload object instead of the `self` instance.
Following the same principle `CallableWithSubjectArgProcessor` types accept a subject instead of the `self` instance

> **WARNING**:
> 
> Like with `CallableWithSelfArgProcessor`, the `subject` and `payload` parameter names are locked, you can only use them, otherwise they will not work.

``` python
# Let's assume we implemented 2 functions like the ones imported here.
from my_application_rule_functions import FormatMessage, Print 

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            processing: [
                FormatMessage(lambda subject: subject.name), # CallableWithSubjectArgProcessor
                Print(lambda payload: payload["message"]),   # CallableWithPayloadArgProcessor
            ],
        },
    },
}
```

> Some `RuleFunctions` accept callables as parameters:
> 
> It is important to note that this **does not conflict** with the argument processors, indeed, the two things can coexist in the same argument.
>  
> For example, `OnSubjectPropertyChanged` is a filter which, as its name suggests, check whether a given subject property has been changed.
> 
> It also supports 2 additional kwargs: `value` and `old_value`.
> If those are assigned static values, the comparison will be simply be performed between the corresponding value in the payload (`value` and `old_value` are always present in `subject-property-changed` event).
> 
> However, it is also possible to assign a boolean function to these parameters which takes `value` and `old_value` as arguments.

``` python
from krules_core.base_functions import OnSubjectPropertyChanged

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            filters: [
                OnSubjectPropertyChanged(
                    "temperature",
                    value=lambda value,old_value: value > 25 and old_value is None,
                ),
            ],
        },
    },
}
```

Suppose we want also to pass the subject information to the *old_value* function.
 
``` python
from krules_core.base_functions import OnSubjectPropertyChanged

# ...

rulesdata=[
    {
        rulename: "test",
        subscribe_to: "...",
        ruledata: {
            filters: [
                OnSubjectPropertyChanged(
                    "temperature",
                    value=lambda subject: lambda value, old_value: subject.status == "READY" and value > 25 and old_value is None,
                ),
            ],
        },
    },
}
```

In this case the first lambda function will be called by the argument processor and its result, which is itself a lambda function, will be passed to `value`.

To get the detail of all the core processors available, please refer to the [***KRules API Reference (TODO)***](./TODO).

## Custom argument processors

Even if the default argument processors already cover most of the application cases, it is possible that, during application development, the need to satisfy specific requirements emerges.

You can implement those specific cases by creating custom argument processors.

To do that you can follow this guide

## Implementing custom Argument Processors

Let's suppose we want to develop an application that needs to access the elements nested within the payload, contemplating both the extraction of a single value and an array of elements. The smartest way to do this is to exploit the *json path* paradigm.

A possible implementation of this custom argument processor could be the following:

``` python
import jsonpath_rw_ext as jp
from krules_core.arg_processors import processors, BaseArgProcessor

#...

class JPPayloadMatchBase:
    """
    JPPayloadMatchBase is an abstract class representing
    a json path matcher.
    """

    def __init__(self, expr):
        """
        __init__ initializes class properties.
        Parameters
        ----------
            expr (str):
            The json path expression string used to match.
        """
        self._expr = expr

    def match(self, instance):
        """
        match implements the interface and is used to 
        run the matching with the argument processor.
        Parameters
        ----------
            instance (dict):
            The argument instance to process. Has a 'payload' attribute.
        """
        raise NotImplementedError()

class JPMatcherMulti(JPPayloadMatchBase):
    """
    JPMatcherMulti is a class representing
    a json path matcher with full path match.
    """

    def match(self, instance):
        """
        match implements the interface and is used to 
        run the matching with the argument processor.
        
        Parameters
        ----------
            instance (dict):
            The argument instance to process. Has a 'payload' attribute.
        """
        return jp.match(self._expr, instance.payload)

class JPMatcherSingle(JPPayloadMatchBase):
    """
    JPMatcherMulti is a class representing
    a json path matcher with single path element match.
    """

    def match(self, instance):
        """
        match implements the interface and is used to 
        run the matching with the argument processor.
        
        Parameters
        ----------
            instance (dict):
            The argument instance to process. Has a 'payload' attribute.
        """
        return jp.match1(self._expr, instance.payload)

class JPProcessor(BaseArgProcessor):
    """
    JPProcessor is the custom argument processor which matches 
    json paths.
    """

    @staticmethod
    def interested_in(arg):
        """
        Checks whether if the passed arg meets the requirements for it to be processed.

        Parameters
        ----------
        arg (str):
            The argument that needs to be processed.

        Returns
        ----------
        is_interested_in (bool): True if the argument should be processed, False otherwise.
        """
        return isinstance(arg, JPPayloadMatchBase)

    def process(self, instance):
        """
        Performs the actual argument processing, matching json paths using the matcher.

        Parameters
        ----------
        instance (dict):
            The argument instance to process. Has a 'payload' attribute.
        """
        return self._arg.match(instance)

processors.append(JPProcessor)

rulesdata=[
    {
        rulename: "test-with-jp-expr",
        subscribe_to: "test-argprocessors-jp-match",
        ruledata: {
            filters: [
                CheckValues("$.elems[*].value"),
            ],
            processing: [
                Print(JPMatcherSingle("$.elems[?id==2].message")),
            ],
        },
    },
]
```

Let's analyze the implementation in details.

We will not dwell too much on the implementation of the *jp_match* and *jp_match1* classes because they are only ancillary to the example. What's interesting is that they both extend the *JPPayloadMatchBase* class and override the definitive match method in it, in which the expression in the json path format is resolved to extract the data from the payload.

Let's now move on to the actual argument processor, the **JPProcessor** class. In the *interested_in* method, it verifies that the argument is an instance of the *JPPayloadMatchBase* class. The *process* method instead invokes the match method by passing it the instance of the RuleFunctionBase that will use the wrapped argument.

A fundamental step is the extension of the argument processor pool.

```python
from krules_core.arg_processors import processors, BaseArgProcessor
#...

processors.append(JPProcessor)

#...
```

Doing this you add the new class (or new classes) to the argument processors pool.

At this point it is possible to use the 2 classes just implemented as arguments of the next RuleFunctions.