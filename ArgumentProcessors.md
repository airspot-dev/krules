# How arguments are processed #

A **Rule** is a static structure which is instantiated on the startup and it remains in the memory for the entire duration of the process that contains it.

Take for example the *Print* RuleFunction which can be used to print a text upon receipt of a certain event.

```python
class Print(RuleFunctionBase):

    def execute(self, text):
        print(text)
# ...
rulesdata=[{
        processing: [
            Print("Hello World!")
        ]
    }]
```

In this example, on the startup, will be created a Print instance passing to it a predefined string.
However a reactive system, by its very definition, must react to state system changes, and therefore it is logical to assume that even the parameters of its functions can change with it by accessing information at runtime during the execution of the Rule itself.
So let's assume that, instead a predefined string, you want to print the content of "message" field of the event payload.
The first option is to create a specific RuleFunction which reads the "message" variable content from the payload.

```python
class PrintMessageFromPayload(RuleFunctionBase):

    def execute(self):
        print(self.payload["message"])
# ...
rulesdata=[{
        processing: [
            PrintMessageFromPayload()
        ]
    }]
```
   
While this function does its job perfectly, it is clearly too much specific.
However, it is possible to achieve the same effect with the generic function defined above:

```python
# ...
rulesdata=[{
        processing: [
            Print(lambda payload: payload["message"])
        ]
    }]
```

This is possible thanks to the **argument processors**.
An argument processor is a class that implement 2 simple methods:

- **interested_in(arg)** : A boolean method which, receiving an argument, it checks whether if it meets the requirements for it to be processed by the argument processor;
- **process(instance)** : It is the method where the argument conversion actually take place starting from the instance of the rule that is being currently executed allowing, for example, access to the status information at runtime.

At the startup, each argument of each RuleFunction is examined in order to identify which is the argument processor interested in argument and consequently instantiate it.
If no argument processor declares itself interested, the argument will be treated as it is without being processed at runtime.

## Available argument processor 

The available argument processors are defined in the module **krules_core.arg_processors** and are the following:

### SimpleCallableArgProcessor

It allows to use a simple function as parameter that will be invoked without providing further parameters.

```python
# ...
rulesdata=[{
        processing: [
            SetSubjectProperty("proc_time", datetime.now)
        ]
    }]
```

### CallableWithSelfArgProcessor

It allows to use a function to which the running RuleFunction instance is passed so that you can access current status information such as the payload or subject. A function, to be eligible to be wrapped to this argument processor, must have only one argument called **self**.

```python
# ...
rulesdata=[{
        processing: [
            PyCall(requests.get, args=lambda self: (
                "http://server.address/{}?attr={}".format(
                    str(self.subject),
                    self.payload["req_attr"]
                ),
            )
        ]
    }]
```

### Warning
As the next 2 argument processors, the parameter name is discriminating and not optional.

```python
# ...
rulesdata=[{
        processing: [
            PyCall(requests.get, args=lambda s: (
                "http://server.address/{}?attr={}".format(
                    str(s.subject),
                    s.payload["req_attr"]
                ),
            )
        ]
    }]
```

Defining *PyCall* in this way **the args parameter will not be processed from CallableWithSelf.**

### CallableWithPayloadArgProcessor and CallableWithSubjectArgProcessor

Following the concept of the **CallableWithSelfArgProcessor**, 2 other argument processors have been implemented which, however, instead of receiving the entire state, focus only on 2 parts of it, respectively the payload and the subject.

```python
# ...
ruledata={
        processing: [
            FormatMessage(lambda subject: subject.name) # CallableWithSubjectArgProcessor
            Print(lambda payload: payload["message"]), # CallableWithPayloadArgProcessor
        ]
    }
```

Some RuleFunctions accept callables as parameters, it is important to note that this does not conflict at all with the argument processors, indeed, the two things can coexist in the same argument. 
For example, SubjectPropertyChanged is a filter which, as its name suggests, check whether a given subject property has been changed. Also can be specified 2 kwargs: value and old_value. If these are assigned static values, the comparison will be simply be performed with the corresponding value in the payload (value and old_value are always present in subject-property-changed event). However, it is also possible to assign a boolean function to these parameters which takes value and old_value as arguments.

```python
# ...
ruledata={
        filters: [
            SubjectPropertyChanged("temperature", old_value=lambda old_value, value: value > 25 and old_value is None ),
        ]
    }
```

Suppose we want also to pass the subject information to the *old_value* function.
 
```python
# ...
ruledata={
        filters: [
            SubjectPropertyChanged("temperature", old_value=lambda subject: lambda old_value, value: subject.status == "READY" and value > 25 and old_value is None ),
        ]
    }
```

In this case the first lambda function will be called by the argument processor and its result, which is itself a lambda function, will be passed to old_value.

## Custom argument processors

Even if the default argument processors already cover most of the application cases, it is possible that, during application development, the need to satisfy specific requirements emerges by creating custom argument processors.

Suppose we want to develop an application that needs to access the elements nested within the payload, contemplating both the extraction of a single value and an array of elements, perhaps to use them in some filter. The smartest way to do this is to exploit the json path paradigm.
A possible implementation could be the following:

```python
from krules_core.arg_processors import processors, BaseArgProcessor
#...

class JPPayloadMatchBase:

    def __init__(self, expr):
        self._expr = expr

    def match(self, instance):
        raise NotImplementedError()

class jp_match(JPPayloadMatchBase):

    def match(self, instance):
        return jp.match(self._expr, instance.payload)

class jp_match1(JPPayloadMatchBase):

    def match(self, instance):
        return jp.match1(self._expr, instance.payload)

class JPProcessor(BaseArgProcessor):

    @staticmethod
    def interested_in(arg):
        return isinstance(arg, JPPayloadMatchBase)

    def process(self, instance):
        return self._arg.match(instance)

processors.append(JPProcessor)

RuleFactory.create(
    "test-with-jp-expr",
    subscribe_to="test-argprocessors-jp-match",
    data={
        filters: [
            CheckValues("$.elems[*].value")
        ]
        processing: [
            Print(jp_match1("$.elems[?id==2].message"))
        ]
    }
)
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