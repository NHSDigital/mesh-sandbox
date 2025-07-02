from dataclasses import fields, is_dataclass
from datetime import date, datetime
from typing import Any, Optional, TypeVar, cast, get_args, get_origin

_NoneType = type(None)


def optional_origin_type(original_type: type) -> type:
    """
    if the target type is Optional, this will return the wrapped type
    """
    if original_type.__class__.__name__ != "_UnionGenericAlias":
        return original_type
    args = get_args(original_type)
    if len(args) != 2:
        return original_type

    args = tuple(arg for arg in args if arg != _NoneType)
    if len(args) != 1:
        return original_type
    return cast(type, args[0])


def is_dataclass_instance(obj) -> bool:
    return is_dataclass(obj) and not isinstance(obj, type)


def serialise_value(value) -> Optional[Any]:
    if value is None:
        return None

    if is_dataclass_instance(value):
        class_serialised = serialise_model(value)
        return class_serialised

    if isinstance(value, dict):
        dict_serialised = {k: serialise_value(v) for k, v in value.items()}
        return dict_serialised

    if isinstance(value, (list, tuple)):
        if not value:
            return None
        list_serialised = [serialise_value(v) for v in value]
        return list_serialised

    if isinstance(value, (date, datetime)):
        value = value.isoformat()

    if isinstance(value, set) and not value:
        return None

    return value


def serialise_model(model) -> Optional[dict[str, Any]]:
    if model is None:
        return None

    if not is_dataclass_instance(model):
        raise TypeError(f"type {type(model)} is not a dataclass")

    result: dict[str, Any] = {}

    for field in fields(model):
        value = getattr(model, field.name)
        if value is None:
            # don't store None values.
            continue

        if field.type == Optional[str] and value == "":
            continue

        value = serialise_value(value)

        result[field.name] = value

    return result


# pylint: disable=too-many-return-statements
def _deserialise_value(field_type, value):
    field_type = optional_origin_type(field_type)

    if field_type in (str, bytes, bool):
        return value

    if is_dataclass(field_type):
        return deserialise_model(value, field_type)  # type: ignore

    if field_type in (int, float):
        return field_type(value)

    if field_type == datetime:
        return datetime.fromisoformat(value)

    if field_type == date:
        return date.fromisoformat(value)

    origin_type = get_origin(field_type)

    if origin_type is list:
        item_type = get_args(field_type)[0]
        return [_deserialise_value(item_type, val) for val in value]

    if origin_type is dict:
        val_type = get_args(field_type)[1]
        return {key: _deserialise_value(val_type, val) for key, val in value.items()}

    if origin_type is frozenset:
        return frozenset(val for val in value)

    return value


TModel = TypeVar("TModel")  # pylint: disable=invalid-name


def deserialise_model(model_dict: dict[str, Any], model_type: type[TModel]) -> Optional[TModel]:
    if model_dict is None:
        return None

    if not is_dataclass(model_type):
        raise TypeError(f"type {model_type} is not a dataclass")

    model_fields = fields(model_type)

    deserialised: dict[str, Any] = {}
    for field in model_fields:
        value = model_dict.get(field.name)
        if value is None:
            continue

        deserialised[field.name] = _deserialise_value(field.type, value)

    return model_type(**deserialised)  # type: ignore[return-value]
