from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from unittest.mock import patch
from dojo.models import Dojo_User, Product_Type, Product_Type_Member, Product, Product_Member, Engagement, \
    Test, Finding, Endpoint, Dojo_Group, Product_Group, Product_Type_Group
import dojo.authorization.authorization
from dojo.authorization.authorization import role_has_permission, get_roles_for_permission, \
    user_has_permission_or_403, user_has_permission, \
    RoleDoesNotExistError, PermissionDoesNotExistError
from dojo.authorization.roles_permissions import Permissions, Roles


class TestAuthorization(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = Dojo_User()
        cls.user.id = 1
        cls.product_type = Product_Type()
        cls.product_type.id = 1
        cls.product_type_member = Product_Type_Member()
        cls.product_type_member.id = 1
        cls.product = Product()
        cls.product.id = 1
        cls.product_member = Product_Member()
        cls.product_member.id = 1
        cls.product.prod_type = cls.product_type
        cls.engagement = Engagement()
        cls.engagement.product = cls.product
        cls.test = Test()
        cls.test.engagement = cls.engagement
        cls.finding = Finding()
        cls.finding.test = cls.test
        cls.endpoint = Endpoint()
        cls.endpoint.product = cls.product

        cls.product_type_member_reader = Product_Type_Member()
        cls.product_type_member_reader.user = cls.user
        cls.product_type_member_reader.product_type = cls.product_type
        cls.product_type_member_reader.role = Roles.Reader

        cls.product_type_member_owner = Product_Type_Member()
        cls.product_type_member_owner.user = cls.user
        cls.product_type_member_owner.product_type = cls.product_type
        cls.product_type_member_owner.role = Roles.Owner

        cls.product_member_reader = Product_Member()
        cls.product_member_reader.user = cls.user
        cls.product_member_reader.product = cls.product
        cls.product_member_reader.role = Roles.Reader

        cls.product_member_owner = Product_Member()
        cls.product_member_owner.user = cls.user
        cls.product_member_owner.product = cls.product
        cls.product_member_owner.role = Roles.Owner

        cls.group = Dojo_Group()
        cls.group.id = 1

        cls.product_group_reader = Product_Group()
        cls.product_group_reader.id = 1
        cls.product_group_reader.product = cls.product
        cls.product_group_reader.group = cls.group
        cls.product_group_reader.role = Roles.Reader

        cls.product_group_owner = Product_Group()
        cls.product_group_owner.id = 2
        cls.product_group_owner.product = cls.product
        cls.product_group_owner.group = cls.group
        cls.product_group_owner.role = Roles.Owner

        cls.product_type_group_reader = Product_Type_Group()
        cls.product_type_group_reader.id = 1
        cls.product_type_group_reader.product_type = cls.product_type
        cls.product_type_group_reader.group = cls.group
        cls.product_type_group_reader.role = Roles.Reader

        cls.product_type_group_owner = Product_Type_Group()
        cls.product_type_group_owner.id = 2
        cls.product_type_group_owner.product_type = cls.product_type
        cls.product_type_group_owner.group = cls.group
        cls.product_type_group_owner.role = Roles.Owner

    def test_role_has_permission_exception(self):
        with self.assertRaisesMessage(RoleDoesNotExistError,
                'Role 9999 does not exist'):
            role_has_permission(9999, Permissions.Product_Type_Edit)

    def test_role_has_permission_true(self):
        result = role_has_permission(Roles.Maintainer, Permissions.Product_Type_Edit)
        self.assertTrue(result)

    def test_role_has_permission_false(self):
        result = role_has_permission(Roles.Reader, Permissions.Product_Type_Edit)
        self.assertFalse(result)

    def test_get_roles_for_permission_exception(self):
        with self.assertRaisesMessage(PermissionDoesNotExistError,
                'Permission 9999 does not exist'):
            get_roles_for_permission(9999)

    def test_get_roles_for_permission_success(self):
        result = get_roles_for_permission(Permissions.Product_Type_Manage_Members)
        expected = {Roles.Maintainer, Roles.Owner}
        self.assertEqual(result, expected)

    def test_user_has_permission_or_403_exception(self):
        with self.assertRaises(PermissionDenied):
            user_has_permission_or_403(self.user, self.product_type, Permissions.Product_Type_Delete)

    @patch('dojo.models.Product_Type_Member.objects')
    def test_user_has_permission_or_403_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_type_member_owner]

        user_has_permission_or_403(self.user, self.product_type, Permissions.Product_Type_Delete)

        mock_foo.filter.assert_called_with(user=self.user)

    def test_user_has_permission_exception(self):
        with self.assertRaisesMessage(dojo.authorization.authorization.NoAuthorizationImplementedError,
                'No authorization implemented for class Product_Type_Member and permission 1007'):
            user_has_permission(self.user, self.product_type_member, Permissions.Product_Type_Delete)

    def test_user_has_permission_product_type_no_member(self):
        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_View)
        self.assertFalse(result)

    @patch('dojo.models.Product_Type_Member.objects')
    def test_user_has_permission_product_type_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_type_member_reader]

        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_Delete)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=self.user)

    def test_user_has_permission_superuser(self):
        self.user.is_superuser = True

        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_Delete)

        self.assertTrue(result)

        self.user.is_superuser = False

    @override_settings(AUTHORIZATION_STAFF_OVERRIDE=True)
    def test_user_has_permission_staff_override(self):
        self.user.is_staff = True

        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_Delete)

        self.assertTrue(result)

        self.user.is_staff = False

    @patch('dojo.models.Product_Type_Member.objects')
    def test_user_has_permission_product_type_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_type_member_owner]

        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    def test_user_has_permission_product_no_member(self):
        result = user_has_permission(self.user, self.product, Permissions.Product_View)
        self.assertFalse(result)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_product_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_reader]

        result = user_has_permission(self.user, self.product, Permissions.Product_Delete)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Type_Member.objects')
    def test_user_has_permission_product_product_type_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_type_member_owner]

        result = user_has_permission(self.user, self.product, Permissions.Product_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_product_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_owner]

        result = user_has_permission(self.user, self.product, Permissions.Product_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_engagement_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_reader]

        result = user_has_permission(self.user, self.engagement, Permissions.Engagement_Edit)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_engagement_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_owner]

        result = user_has_permission(self.user, self.engagement, Permissions.Engagement_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_test_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_reader]

        result = user_has_permission(self.user, self.test, Permissions.Test_Edit)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_test_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_owner]

        result = user_has_permission(self.user, self.test, Permissions.Test_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_finding_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_reader]

        result = user_has_permission(self.user, self.finding, Permissions.Finding_Edit)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_finding_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_owner]

        result = user_has_permission(self.user, self.finding, Permissions.Finding_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_endpoint_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_reader]

        result = user_has_permission(self.user, self.endpoint, Permissions.Endpoint_Edit)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=self.user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_endpoint_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_member_owner]

        result = user_has_permission(self.user, self.endpoint, Permissions.Endpoint_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=self.user)

    def test_user_has_permission_product_type_member_success_same_user(self):
        result = user_has_permission(self.user, self.product_type_member_owner, Permissions.Product_Type_Member_Delete)
        self.assertTrue(result)

    @patch('dojo.models.Product_Type_Member.objects')
    def test_user_has_permission_product_type_member_no_permission(self, mock_foo):
        other_user = User()
        other_user.id = 2
        product_type_member_other_user = Product_Type_Member()
        product_type_member_other_user.id = 2
        product_type_member_other_user.user = other_user
        product_type_member_other_user.product_type = self.product_type
        product_type_member_other_user.role = Roles.Reader
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [product_type_member_other_user]

        result = user_has_permission(other_user, self.product_type_member_owner, Permissions.Product_Type_Member_Delete)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=other_user)

    @patch('dojo.models.Product_Type_Member.objects')
    def test_user_has_permission_product_type_member_success(self, mock_foo):
        other_user = User()
        other_user.id = 2
        product_type_member_other_user = Product_Type_Member()
        product_type_member_other_user.id = 2
        product_type_member_other_user.user = other_user
        product_type_member_other_user.product_type = self.product_type
        product_type_member_other_user.role = Roles.Owner
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [product_type_member_other_user]

        result = user_has_permission(other_user, self.product_type_member_reader, Permissions.Product_Type_Member_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=other_user)

    def test_user_has_permission_product_member_success_same_user(self):
        result = user_has_permission(self.user, self.product_member_owner, Permissions.Product_Member_Delete)
        self.assertTrue(result)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_product_member_no_permission(self, mock_foo):
        other_user = User()
        other_user.id = 2
        product_member_other_user = Product_Member()
        product_member_other_user.id = 2
        product_member_other_user.user = other_user
        product_member_other_user.product = self.product
        product_member_other_user.role = Roles.Reader
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [product_member_other_user]

        result = user_has_permission(other_user, self.product_member_owner, Permissions.Product_Member_Delete)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(user=other_user)

    @patch('dojo.models.Product_Member.objects')
    def test_user_has_permission_product_member_success(self, mock_foo):
        other_user = User()
        other_user.id = 2
        product_member_other_user = Product_Member()
        product_member_other_user.id = 2
        product_member_other_user.user = other_user
        product_member_other_user.product = self.product
        product_member_other_user.role = Roles.Owner
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [product_member_other_user]

        result = user_has_permission(other_user, self.product_member_reader, Permissions.Product_Member_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(user=other_user)

    @patch('dojo.models.Product_Group.objects')
    def test_user_has_group_product_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_group_reader]

        result = user_has_permission(self.user, self.product, Permissions.Product_Delete)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(group__users=self.user)

    @patch('dojo.models.Product_Group.objects')
    def test_user_has_group_product_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_group_owner]

        result = user_has_permission(self.user, self.product, Permissions.Product_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(group__users=self.user)

    @patch('dojo.models.Product_Type_Group.objects')
    def test_user_has_group_product_type_no_permissions(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_type_group_reader]

        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_Delete)

        self.assertFalse(result)
        mock_foo.filter.assert_called_with(group__users=self.user)

    @patch('dojo.models.Product_Type_Group.objects')
    def test_user_has_group_product_type_success(self, mock_foo):
        mock_foo.select_related.return_value = mock_foo
        mock_foo.filter.return_value = [self.product_type_group_owner]

        result = user_has_permission(self.user, self.product_type, Permissions.Product_Type_Delete)

        self.assertTrue(result)
        mock_foo.filter.assert_called_with(group__users=self.user)
