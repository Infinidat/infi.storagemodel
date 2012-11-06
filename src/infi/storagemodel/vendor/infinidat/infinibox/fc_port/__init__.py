class InfinidatFiberChannelPort(object):
    def __init__(self, relative_target_port_identifer, target_port_group):
        super(InfinidatFiberChannelPort, self).__init__()
        self._relative_target_port_identifer = relative_target_port_identifer
        self._target_port_group = target_port_group

    def get_node_id(self):
        return (self._relative_target_port_identifer >> 8) & 0xff

    def get_port_id(self):
        return self._relative_target_port_identifer & 0xff

    def get_port_group(self):
        return self._target_port_group
