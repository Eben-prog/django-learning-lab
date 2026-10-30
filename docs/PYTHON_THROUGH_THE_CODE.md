# Python through this codebase

Each concept is shown with the real file where it appears and a Java / JavaScript comparison.

**Variables and types.** No declarations: `page_size = 10`, `DEBUG = env_bool("DJANGO_DEBUG", False)` (`config/settings.py`). Types belong to values, not names (like JS). Core types: `int`, `str`, `bool`, `float`, `None`.
**`None`** is Python's `null`/`undefined` in one. Test with `is None` / `is not None` (`if user is None:` in `accounts/views.py`), never `== None`. Falsy values: `None`, `0`, `""`, `[]`, `{}`, so `if not raw_token:` also catches an empty string.

**Collections.** `list` `[1, 2]` (ArrayList/array), `tuple` `("a", "b")` (immutable, used for `AUTH_HEADER_TYPES`, model `choices`), `set` `{"open", "closed"}` (HashSet; `ALLOWED_TRANSITIONS` values in `tickets/services.py`), `dict` `{"status": "open"}` (HashMap/object literal; settings, `ALLOWED_TRANSITIONS`, API payloads). Access `d["k"]` (KeyError if missing) or `d.get("k", default)`.

**Functions and arguments.** `def change_status(ticket, new_status, actor):`. Keyword arguments at call sites: `serializer.save(created_by=request.user)`, so order doesn't matter and calls read clearly. Defaults: `def env_bool(name, default=False)`. `*args, **kwargs` collect extra positional/keyword arguments, so you will see `def create(self, request, *args, **kwargs)` everywhere in Django: it means "accept whatever the framework passes". Functions are values: `loader=...`, `permission_classes=[...]` hold classes themselves.

**Classes and objects.** `class Ticket(models.Model):` is *inheritance* (Java `extends`). `self` is the explicit `this`. Class attributes (`title = models.CharField(...)`) are **field declarations** that the ORM metaclass turns into columns; this is closer to a JPA `@Column` annotated field than to a plain Java field. A Django model class is the entity *and* the repository entry point (`Ticket.objects`). Nested `class Meta:` holds configuration (ordering, indexes, constraints); `class Status(models.TextChoices)` is a Java `enum` with labels.
**Composition vs inheritance:** DRF *composes* behaviour by listing classes: `permission_classes = [IsAuthenticated, TicketObjectPermission]`: Spring-like "plug in checkers" instead of subclassing for every combination. *Inheritance* is used where it fits: `TicketUpdateSerializer(TicketCreateSerializer)` reuses fields and validators. Python allows multiple inheritance (`TextChoices(str, Choices)`); you mostly *use* it, not write it.

**Properties.** `@property def is_support_staff(self)` (`accounts/models.py`) is a getter used like a field: `user.is_support_staff`, with no parentheses.

**Modules and imports.** Each `.py` file is a module; a folder with `__init__.py` is a package. `from tickets.models import Ticket` ≈ Java `import tickets.models.Ticket`. Import paths start from the folder containing `manage.py`. `ImportError`/`ModuleNotFoundError` = wrong path, missing package, or inactive virtualenv.

**Virtual environments.** `python -m venv .venv` makes an isolated copy of the interpreter with its own packages (Maven per-project dependencies / `node_modules`). `requirements.txt` is `package.json`; `pip install -r requirements.txt` is `npm install`. Pin versions (`Django==5.1.4`) for reproducibility.

**Exceptions.** `try/except/finally` (same idea as Java). Catch the specific type: `except TokenError:` (`accounts/views.py`); raise with `raise ValidationError({...})` (`tickets/services.py`). Django/DRF convert certain exceptions into HTTP responses, so `raise PermissionDenied` becomes a 403 without returning anything. Python exceptions are all unchecked.

**Decorators.** `@transaction.atomic` above `change_status` wraps the function in BEGIN/COMMIT/ROLLBACK, like Spring's `@Transactional`. `@action(detail=True, methods=["post"])` registers a route, like `@PostMapping`. `@property`, `@api_view`, `@extend_schema` are the same mechanism: a function that takes your function and returns an enhanced one.

**Type hints.** `def env_list(name: str, default: str = "") -> list[str]:`, `ALLOWED_TRANSITIONS: dict[str, set[str]]`. They document intent and help editors/mypy but **are not enforced at runtime** (unlike Java). `str | None` means "string or None" (nullable).

**List/dict comprehensions.** `[item.strip() for item in raw.split(",") if item.strip()]` (`env_list`), `{row["priority"]: row["n"] for row in ...}` (`dashboard/services.py`). Equivalent to `map/filter` in JS or a stream in Java: transform and filter a collection in one expression.

**Context managers (`with`).** `with connection.cursor() as cursor:` (`config/views.py`) guarantees the resource is closed, like Java try-with-resources. `with transaction.atomic():` and `with pytest.raises(IntegrityError):` (tests) use the same idea: setup on entry, cleanup/assertion on exit.

**Mutable objects and shared state.** Lists/dicts are passed **by reference** and can be mutated by callees. Classic trap: a mutable default argument (`def f(x=[])`) is created once and shared between calls; use `None` and create inside. Django model *field defaults* must be callables or immutables for the same reason (`default=dict`, not `default={}`). Strings, ints, tuples are immutable.

**Strings.** f-strings (`f"#{self.pk} {self.title}"`) are JS template literals. Triple quotes make multi-line strings (docstrings, which document functions and show up in Swagger/Admin).

**Truthiness and chaining.** `a and b`/`or`/`not` instead of `&&`/`||`/`!`. `0 < x < 10` works. `x if cond else y` is the ternary (`timezone.now() if new_status == S.CLOSED else None`).

**How Django uses classes and functions.** Class-based pieces (models, serializers, viewsets, permissions) are *declarative*: you subclass and fill in attributes or override hooks (`get_queryset`, `validate_title`, `has_object_permission`) and the framework calls you (inversion of control, like Spring). Function-based pieces (`health` view, `services.py`) are plain functions. Rule of thumb for debugging: find which hook of which base class is being overridden, then read the framework's documentation for *when* it is called.

**Concrete comparisons asked for.**
* Java class vs Django model: a Java entity class + Hibernate mapping + repository interface ⇒ one Django class; constraints in `Meta`; schema changes via migrations instead of `hbm2ddl`.
* Express route handler vs DRF view: `app.post('/tickets', auth, async (req,res)=>{ validate(req.body); const t = await Ticket.create(...); res.status(201).json(t) })` ⇒ `TicketViewSet.create`, where `auth` is `permission_classes`/`authentication_classes`, `validate` is the serializer, `Ticket.create` is the ORM, and `res.json` is `Response`.
* Spring Boot controller + DTO + `@Valid` + service + repository ⇒ ViewSet + Serializer + (optional `services.py`) + `Model.objects`.
