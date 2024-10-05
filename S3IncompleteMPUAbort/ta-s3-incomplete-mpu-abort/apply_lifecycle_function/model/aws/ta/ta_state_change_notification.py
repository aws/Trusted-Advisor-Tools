# coding: utf-8
import pprint
import six

class TAStateChangeNotification(object):
    _types = {
        'check_name': 'str',
        'check_item_detail': 'dict(str, str)',
        'status': 'str',
        'resource_id': 'str',
        'uuid': 'str'
    }

    _attribute_map = {
        'check_name': 'check-name',
        'check_item_detail': 'check-item-detail',
        'status': 'status',
        'resource_id': 'resource_id',
        'uuid': 'uuid'
    }

    def __init__(self, check_name=None, check_item_detail=None, status=None, resource_id=None, uuid=None):
        self._check_name = None
        self._check_item_detail = None
        self._status = None
        self._resource_id = None
        self._uuid = None
        self.discriminator = None
        self.check_name = check_name
        self.check_item_detail = check_item_detail
        self.status = status
        self.resource_id = resource_id
        self.uuid = uuid

    @property
    def check_name(self):
        return self._check_name

    @check_name.setter
    def check_name(self, check_name):
        self._check_name = check_name

    @property
    def check_item_detail(self):
        return self._check_item_detail

    @check_item_detail.setter
    def check_item_detail(self, check_item_detail):
        self._check_item_detail = check_item_detail

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def resource_id(self):
        return self._resource_id

    @resource_id.setter
    def resource_id(self, resource_id):
        self._resource_id = resource_id

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        self._uuid = uuid

    def to_dict(self):
        result = {}
        for attr, _ in six.iteritems(self._types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        return result

    def to_str(self):
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        if not isinstance(other, TAStateChangeNotification):
            return False
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other