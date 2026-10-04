def allow(context):
    if not context.get('requires_authentication'):
        return True
    auth = context.get('authenticated_user_id')
    if auth is None:
        return False
    owner = context.get('owner_id')
    if owner is not None and owner != auth:
        return False
    return True
