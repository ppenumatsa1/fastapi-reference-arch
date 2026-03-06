# Error Response Contract

Use a consistent error envelope across handlers and routes.

## App Errors

Raised from `AppError` subclasses and mapped by global handlers.

```json
{
  "error": {
    "code": "not_found",
    "message": "Todo not found"
  }
}
```

## Validation Errors

Returned for request validation failures.

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed"
  },
  "details": [
    {
      "loc": ["body", "title"],
      "msg": "Value error, title must not be empty or whitespace",
      "type": "value_error"
    }
  ]
}
```

## Unhandled Errors

Returned by fallback exception handler.

```json
{
  "error": {
    "code": "internal_error",
    "message": "Internal server error"
  }
}
```
