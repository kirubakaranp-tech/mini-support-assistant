import json

from orders_db import find_order

CUSTOMERS = {
    1: {"id": 1, "name": "Sixer Sundar", "plan": "Basic", "email": "sundar@example.com"},
    2: {"id": 2, "name": "Googly Ganesh", "plan": "Premium", "email": "ganesh@example.com"},
    3: {"id": 3, "name": "Captain Kumar", "plan": "Standard", "email": "kumar@example.com"},
    4: {"id": 4, "name": "Yorker Yamini", "plan": "Premium", "email": "yamini@example.com"},
    5: {"id": 5, "name": "Duck-out Dinesh", "plan": "Basic", "email": "dinesh@example.com"},
}


def get_customer(customer_id):
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"found": False, "error": f"There is no customer with id {customer_id}."}
    return {"found": True, "customer": customer}


def get_order_status(order_id):
    order = find_order(order_id)
    if order is None:
        return {"found": False, "error": f"There is no order with id {order_id}."}
    return {"found": True, "order": order}


TOOL_FUNCTIONS = {
    "get_customer": (get_customer, "customer_id"),
    "get_order_status": (get_order_status, "order_id"),
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Get a customer's name, plan and email by customer id.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "integer", "description": "The customer id, for example 2"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get an order's status and dates by order id.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "integer", "description": "The order id, for example 1042"}},
                "required": ["order_id"],
            },
        },
    },
]


def run_tool(name, arguments_text):
    if name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {name}"}

    function, argument_name = TOOL_FUNCTIONS[name]
    try:
        arguments = json.loads(arguments_text or "{}")
        value = int(arguments[argument_name])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {"error": f"{name} needs a whole number {argument_name}."}

    return function(value)
