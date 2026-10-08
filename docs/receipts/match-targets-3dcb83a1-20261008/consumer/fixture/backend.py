BACKEND = "basic"
match BACKEND:
    case "basic":
        def total(items):
            return sum(items) + 2
    case _:
        def total(items):
            return sum(items)
