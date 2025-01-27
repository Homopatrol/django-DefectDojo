from django.core.exceptions import PermissionDenied
from django.conf import settings
from dojo.request_cache import cache_for_request
from dojo.authorization.roles_permissions import Permissions, Roles, get_roles_with_permissions
from dojo.models import Product_Type, Product_Type_Member, Product, Product_Member, Engagement, \
    Test, Finding, Endpoint, Finding_Group, Product_Group, Product_Type_Group


def user_has_permission(user, obj, permission):

    if user.is_superuser:
        return True

    if user.is_staff and settings.AUTHORIZATION_STAFF_OVERRIDE:
        return True

    if isinstance(obj, Product_Type):
        # Check if the user has a role for the product type with the requested permissions
        member = get_product_type_member(user, obj)
        if member is not None and role_has_permission(member.role, permission):
            return True
        # Check if the user is in a group with a role for the product type with the requested permissions
        for product_type_group in get_product_type_groups(user, obj):
            if role_has_permission(product_type_group.role, permission):
                return True
        return False
    elif (isinstance(obj, Product) and
            permission.value >= Permissions.Product_View.value):
        # Products inherit permissions of their product type
        if user_has_permission(user, obj.prod_type, permission):
            return True

        # Check if the user has a role for the product with the requested permissions
        member = get_product_member(user, obj)
        if member is not None and role_has_permission(member.role, permission):
            return True
        # Check if the user is in a group with a role for the product with the requested permissions
        for product_group in get_product_groups(user, obj):
            if role_has_permission(product_group.role, permission):
                return True
        return False
    elif isinstance(obj, Engagement) and permission in Permissions.get_engagement_permissions():
        return user_has_permission(user, obj.product, permission)
    elif isinstance(obj, Test) and permission in Permissions.get_test_permissions():
        return user_has_permission(user, obj.engagement.product, permission)
    elif isinstance(obj, Finding) and permission in Permissions.get_finding_permissions():
        return user_has_permission(user, obj.test.engagement.product, permission)
    elif isinstance(obj, Finding_Group) and permission in Permissions.get_finding_group_permissions():
        return user_has_permission(user, obj.test.engagement.product, permission)
    elif isinstance(obj, Endpoint) and permission in Permissions.get_endpoint_permissions():
        return user_has_permission(user, obj.product, permission)
    elif isinstance(obj, Product_Type_Member) and permission in Permissions.get_product_type_member_permissions():
        if permission == Permissions.Product_Type_Member_Delete:
            # Every member is allowed to remove himself
            return obj.user == user or user_has_permission(user, obj.product_type, permission)
        else:
            return user_has_permission(user, obj.product_type, permission)
    elif isinstance(obj, Product_Member) and permission in Permissions.get_product_member_permissions():
        if permission == Permissions.Product_Member_Delete:
            # Every member is allowed to remove himself
            return obj.user == user or user_has_permission(user, obj.product, permission)
        else:
            return user_has_permission(user, obj.product, permission)
    elif isinstance(obj, Product_Type_Group) and permission in Permissions.get_product_type_group_permissions():
        return user_has_permission(user, obj.product_type, permission)
    elif isinstance(obj, Product_Group) and permission in Permissions.get_product_group_permissions():
        return user_has_permission(user, obj.product, permission)
    else:
        raise NoAuthorizationImplementedError('No authorization implemented for class {} and permission {}'.
            format(type(obj).__name__, permission))


def user_has_permission_or_403(user, obj, permission):
    if not user_has_permission(user, obj, permission):
        raise PermissionDenied


def get_roles_for_permission(permission):
    if not Permissions.has_value(permission):
        raise PermissionDoesNotExistError('Permission {} does not exist'.format(permission))
    roles_for_permissions = set()
    roles = get_roles_with_permissions()
    for role in roles:
        permissions = roles.get(role)
        if permission in permissions:
            roles_for_permissions.add(role)
    return roles_for_permissions


def role_has_permission(role, permission):
    if not Roles.has_value(role):
        raise RoleDoesNotExistError('Role {} does not exist'.format(role))
    roles = get_roles_with_permissions()
    permissions = roles.get(role)
    return permission in permissions


class NoAuthorizationImplementedError(Exception):
    def __init__(self, message):
        self.message = message


class PermissionDoesNotExistError(Exception):
    def __init__(self, message):
        self.message = message


class RoleDoesNotExistError(Exception):
    def __init__(self, message):
        self.message = message


def get_product_member(user, product):
    return get_product_member_dict(user).get(product.id)


@cache_for_request
def get_product_member_dict(user):
    pm_dict = {}
    for product_member in Product_Member.objects.select_related('product').filter(user=user):
        pm_dict[product_member.product.id] = product_member
    return pm_dict


def get_product_type_member(user, product_type):
    return get_product_type_member_dict(user).get(product_type.id)


@cache_for_request
def get_product_type_member_dict(user):
    ptm_dict = {}
    for product_type_member in Product_Type_Member.objects.select_related('product_type').filter(user=user):
        ptm_dict[product_type_member.product_type.id] = product_type_member
    return ptm_dict


def get_product_groups(user, product):
    return get_product_groups_dict(user).get(product.id, [])


@cache_for_request
def get_product_groups_dict(user):
    pg_dict = {}
    for product_group in Product_Group.objects.select_related('product').filter(group__users=user):
        if pg_dict.get(product_group.product.id) is None:
            pgu_list = []
        else:
            pgu_list = pg_dict[product_group.product.id]
        pgu_list.append(product_group)
        pg_dict[product_group.product.id] = pgu_list
    return pg_dict


def get_product_type_groups(user, product_type):
    return get_product_type_groups_dict(user).get(product_type.id, [])


@cache_for_request
def get_product_type_groups_dict(user):
    pgt_dict = {}
    for product_type_group in Product_Type_Group.objects.select_related('product_type').filter(group__users=user):
        if pgt_dict.get(product_type_group.product_type.id) is None:
            pgtu_list = []
        else:
            pgtu_list = pgt_dict[product_type_group.product_type.id]
        pgtu_list.append(product_type_group)
        pgt_dict[product_type_group.product_type.id] = pgtu_list
    return pgt_dict
