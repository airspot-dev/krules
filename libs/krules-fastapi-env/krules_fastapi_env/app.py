import contextvars
import os
import sys
from enum import Enum

import logging
import types
from typing import Optional, List, Dict, Any, Union, Sequence, Type, Callable, Coroutine
from urllib.request import Request

from fastapi import FastAPI, routing, Depends, params
from fastapi.datastructures import Default
#from fastapi.encoders import SetIntStr, DictIntStrAny
from fastapi.routing import APIRoute
from fastapi.types import DecoratedCallable
from fastapi.utils import generate_unique_id
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, Response, JSONResponse
from starlette.routing import BaseRoute
from starlette.types import Scope, Receive, Send, ASGIApp

import krules_env
from krules_core.providers import subject_factory, event_router_factory
from dependency_injector import providers
import json_logging

from .globals import GlobalsMiddleware, g


class KRulesAPIRoute(routing.APIRoute):

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:

        g.subjects = []
        if self.methods and scope["method"] not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse(
                    "Method Not Allowed", status_code=405, headers=headers
                )
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
        for sub in g.subjects:
            sub.store()


class KRulesAPIRouter(routing.APIRouter):

    def __init__(
        self,
        *args, **kwargs,
        # prefix: str = "",
        # tags: Optional[List[Union[str, Enum]]] = None,
        # dependencies: Optional[Sequence[params.Depends]] = None,
        # default_response_class: Type[Response] = Default(JSONResponse),
        # responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        # callbacks: Optional[List[BaseRoute]] = None,
        # routes: Optional[List[routing.BaseRoute]] = None,
        # redirect_slashes: bool = True,
        # default: Optional[ASGIApp] = None,
        # dependency_overrides_provider: Optional[Any] = None,
        # on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        # on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        # deprecated: Optional[bool] = None,
        # include_in_schema: bool = True,
        # generate_unique_id_function: Callable[[APIRoute], str] = Default(
        #     generate_unique_id
        # ),
    ) -> None:
        super(KRulesAPIRouter, self).__init__(
            route_class=KRulesAPIRoute,
            *args, **kwargs,
            # prefix=prefix,
            # tags=tags,
            # dependencies=dependencies,
            # default_response_class=default_response_class,
            # responses=responses,
            # callbacks=callbacks,
            # routes=routes,
            # redirect_slashes=redirect_slashes,
            # default=default,
            # dependency_overrides_provider=dependency_overrides_provider,
            # on_startup=on_startup,
            # on_shutdown=on_shutdown,
            # deprecated=deprecated,
            # include_in_schema=include_in_schema,
            # generate_unique_id_function=generate_unique_id_function
        )

    def api_route(
        self,
        path: str,
        *args, **kwargs,
        # response_model: Any = Default(None),
        # status_code: Optional[int] = None,
        # tags: Optional[List[Union[str, Enum]]] = None,
        # dependencies: Optional[Sequence[params.Depends]] = None,
        # summary: Optional[str] = None,
        # description: Optional[str] = None,
        # response_description: str = "Successful Response",
        # responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        # deprecated: Optional[bool] = None,
        # methods: Optional[List[str]] = None,
        # operation_id: Optional[str] = None,
        # response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        # response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
        # response_model_by_alias: bool = True,
        # response_model_exclude_unset: bool = False,
        # response_model_exclude_defaults: bool = False,
        # response_model_exclude_none: bool = False,
        # include_in_schema: bool = True,
        # response_class: Type[Response] = Default(JSONResponse),
        # name: Optional[str] = None,
        # callbacks: Optional[List[BaseRoute]] = None,
        # openapi_extra: Optional[Dict[str, Any]] = None,
        # generate_unique_id_function: Callable[[APIRoute], str] = Default(
        #     generate_unique_id
        # ),
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            self.add_api_route(
                path,
                func,
                *args, **kwargs,
                # response_model=response_model,
                # status_code=status_code,
                # tags=tags,
                # dependencies=dependencies,
                # summary=summary,
                # description=description,
                # response_description=response_description,
                # responses=responses,
                # deprecated=deprecated,
                # methods=methods,
                # operation_id=operation_id,
                # response_model_include=response_model_include,
                # response_model_exclude=response_model_exclude,
                # response_model_by_alias=response_model_by_alias,
                # response_model_exclude_unset=response_model_exclude_unset,
                # response_model_exclude_defaults=response_model_exclude_defaults,
                # response_model_exclude_none=response_model_exclude_none,
                # include_in_schema=include_in_schema,
                # response_class=response_class,
                # name=name,
                # callbacks=callbacks,
                # openapi_extra=openapi_extra,
                # generate_unique_id_function=generate_unique_id_function,
            )
            return func

        return decorator


class KrulesApp(FastAPI):

    def __init__(
        self,
        *args, **kwargs,
        # debug: bool = False,
        # routes: Optional[List[BaseRoute]] = None,
        # title: str = "FastAPI",
        # description: str = "",
        # version: str = "0.1.0",
        # openapi_url: Optional[str] = "/openapi.json",
        # openapi_tags: Optional[List[Dict[str, Any]]] = None,
        # servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
        # dependencies: Optional[Sequence[Depends]] = None,
        # default_response_class: Type[Response] = Default(JSONResponse),
        # docs_url: Optional[str] = "/docs",
        # redoc_url: Optional[str] = "/redoc",
        # swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
        # swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
        # middleware: Optional[Sequence[Middleware]] = None,
        # exception_handlers: Optional[
        #     Dict[
        #         Union[int, Type[Exception]],
        #         Callable[[Request, Any], Coroutine[Any, Any, Response]],
        #     ]
        # ] = None,
        # on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        # on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        # terms_of_service: Optional[str] = None,
        # contact: Optional[Dict[str, Union[str, Any]]] = None,
        # license_info: Optional[Dict[str, Union[str, Any]]] = None,
        # openapi_prefix: str = "",
        # root_path: str = "",
        # root_path_in_servers: bool = True,
        # responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        # callbacks: Optional[List[BaseRoute]] = None,
        # deprecated: Optional[bool] = None,
        # include_in_schema: bool = True,
        # swagger_ui_parameters: Optional[Dict[str, Any]] = None,
        # generate_unique_id_function: Callable[[routing.APIRoute], str] = Default(
        #     generate_unique_id
        # ),
        # **extra: Any,
    ) -> None:
        super().__init__(
            *args, **kwargs,
            # debug=debug,
            # routes=routes,
            # title=title,
            # description=description,
            # version=version,
            # openapi_url=openapi_url,
            # openapi_tags=openapi_tags,
            # servers=servers,
            # dependencies=dependencies,
            # default_response_class=default_response_class,
            # docs_url=docs_url,
            # redoc_url=redoc_url,
            # swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
            # swagger_ui_init_oauth=swagger_ui_init_oauth,
            # middleware=middleware,
            # exception_handlers= exception_handlers,
            # on_startup=on_startup,
            # on_shutdown=on_shutdown,
            # terms_of_service=terms_of_service,
            # contact=contact,
            # license_info=license_info,
            # openapi_prefix=openapi_prefix,
            # root_path=root_path,
            # root_path_in_servers=root_path_in_servers,
            # responses=responses,
            # callbacks=callbacks,
            # deprecated=deprecated,
            # include_in_schema=include_in_schema,
            # swagger_ui_parameters=swagger_ui_parameters,
            # generate_unique_id_function=generate_unique_id_function,
            # **extra,
        )
        self.router = KRulesAPIRouter(
            *args, **kwargs,
            # routes=routes,
            # dependency_overrides_provider=self,
            # on_startup=on_startup,
            # on_shutdown=on_shutdown,
            # default_response_class=default_response_class,
            # dependencies=dependencies,
            # callbacks=callbacks,
            # deprecated=deprecated,
            # include_in_schema=include_in_schema,
            # responses=responses,
            # generate_unique_id_function=generate_unique_id_function,
        )
        self.setup()
        self.add_middleware(GlobalsMiddleware)
        json_logging.init_fastapi(enable_json=True)
        json_logging.init_request_instrument(self)
        self.logger = logging.getLogger(self.title)
        self.logger.setLevel(int(os.environ.get("LOGGING_LEVEL", logging.INFO)))
        self.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.logger.propagate = False

        # self.g = contextvars.ContextVar("request_global", default=types.SimpleNamespace())

        subject_factory.override(providers.Factory(lambda *_args, **_kw: _g_wrap(subject_factory.cls, *_args, **_kw)))


def _g_wrap(subject_class, *args, **kwargs):

    event_info = kwargs.pop("event_info", {})
    if not getattr(g, "subjects"):
        g.subjects = []
    if event_info is None and len(g.subjects) > 0:
        event_info = g.subjects[0].event_info()
    subject = subject_class(*args, event_info=event_info, **kwargs)
    g.subjects.append(subject)
    return subject
