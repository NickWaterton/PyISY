from ..constants import _change2update_interval
from VarEvents import Property
from time import sleep
from xml.dom import minidom


STATE_PROPERTY = 'ST'
ATTR_ID = 'id'
ATTR_UOM = 'uom'
ATTR_VALUE = 'value'
ATTR_PREC = 'prec'


def parse_xml_properties(xmldoc):
    """
    Args:
        xmldoc: xml document to parse

    Returns:
        (state_val, state_uom, state_prec, aux_props)
    """
    state_val = None
    state_uom = []
    state_prec = ''
    aux_props = []

    props = xmldoc.getElementsByTagName('property')
    if len(props) > 0:
        for prop in props:
            attrs = prop.attributes
            prop_id = attrs[ATTR_ID] if ATTR_ID in attrs else None
            uom = attrs[ATTR_UOM].value if ATTR_UOM in attrs else ''
            val = attrs[ATTR_VALUE].value if ATTR_VALUE in attrs else None
            prec = attrs[ATTR_PREC].value if ATTR_PREC in attrs else '0'
            units = uom.split('/')

            if prop_id == STATE_PROPERTY:
                state_val = val
                state_uom = units
                state_prec = prec
            else:
                aux_props.append({
                    ATTR_ID: prop_id,
                    ATTR_VALUE: val,
                    ATTR_PREC: prec,
                    ATTR_UOM: units
                })

    return state_val, state_uom, state_prec, aux_props


class Node(object):
    """
    This class handles ISY nodes.

    |  parent: The node manager object.
    |  nid: The Node ID.
    |  nval: The current Node value.
    |  name: The node name.
    |  [optional] dimmable: Default True. Boolean of whether the node is
       dimmable.

    :ivar status: A watched property that indicates the current status of the
                  node.
    :ivar hasChildren: Property indicating that there are no more children.
    """

    status = Property(0)
    hasChildren = False

    def __init__(self, parent, nid, nval, name, dimmable=True, spoken=False,
                 uom=None, prec=0, aux_properties=None):
        self.parent = parent
        self._id = nid
        self.dimmable = dimmable
        self.name = name
        self.uom = uom
        self.prec = prec
        self._spoken = spoken
        self.aux_properties = aux_properties or {}

        self.status = nval
        self.status.reporter = self.__report_status__

    def __str__(self):
        """ Returns a string representation of the node. """
        return 'Node(' + self._id + ')'

    def __report_status__(self, new_val):
        self.on(new_val)

    def update(self, waitTime=0, hint=None):
        """ Update the value of the node from the controller. """
        if not self.parent.parent.auto_update:
            sleep(waitTime)
            xml = self.parent.parent.conn.updateNode(self._id)

            if xml is not None:
                try:
                    xmldoc = minidom.parseString(xml)
                except:
                    self.parent.parent.log.error('ISY Could not parse nodes,' +
                                                 'poorly formatted XML.')
                else:
                    state_val, state_uom, state_prec, aux_props = parse_xml_properties(
                        xmldoc)

                    for prop in aux_props:
                        self.aux_properties[prop.get(ATTR_ID)] = prop

                    self.uom = state_uom
                    self.prec = state_prec
                    self.status.update(state_val, silent=True)
                    self.parent.parent.log.info('ISY updated node: ' +
                                                self._id)
            else:
                self.parent.parent.log.warning('ISY could not update node: ' +
                                               self._id)
        elif hint is not None:
            # assume value was set correctly, auto update will correct errors
            self.status.update(hint, silent=True)
            self.parent.parent.log.info('ISY updated node: ' + self._id)

    def off(self):
        """ Turns the node off. """
        response = self.parent.parent.conn.nodeOff(self._id)

        if response is None:
            self.parent.parent.log.warning('ISY could not turn off node: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY turned off node: ' + self._id)
            self.update(_change2update_interval, hint=0)
            return True

    def on(self, val=None):
        """
        Turns the node on.

        |  [optional] val: The value brightness value (0-255) to set the node to
        """
        response = self.parent.parent.conn.nodeOn(self._id, val)

        if response is None:
            self.parent.parent.log.warning('ISY could not turn on node: ' +
                                           self._id)
            return False
        else:
            if val is None:
                self.parent.parent.log.info('ISY turned on node: ' + self._id)
                val = 255
            else:
                self.parent.parent.log.info('ISY turned on node: ' + self._id +
                                            ', To value: ' + str(val))
                val = int(val)
            self.update(_change2update_interval, hint=val)
            return True

    def fastoff(self):
        """ Turns the node fast off. """
        response = self.parent.parent.conn.nodeFastOff(self._id)

        if response is None:
            self.parent.parent.log.warning('ISY could not fast off node: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY turned did a fast off with node: '
                                        + self._id)
            self.update(_change2update_interval, hint=0)
            return True

    def faston(self):
        """ Turns the node fast on. """
        response = self.parent.parent.conn.nodeFastOn(self._id)

        if response is None:
            self.parent.parent.log.warning('ISY could not fast on node: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY did a fast on with node: ' +
                                        self._id)
            self.update(_change2update_interval, hint=255)
            return True

    def bright(self):
        """ Brightens the node by one step. """
        response = self.parent.parent.conn.nodeBright(self._id)

        if response is None:
            self.parent.parent.log.warning('ISY could not brighten node: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY brightened node: ' + self._id)
            self.update(_change2update_interval)
            return True

    def dim(self):
        """ Dims the node by one step. """
        response = self.parent.parent.conn.nodeDim(self._id)

        if response is None:
            self.parent.parent.log.warning('ISY could not dim node: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY dimmed node: ' + self._id)
            self.update(_change2update_interval)
            return True

    def lock(self):
        """ Sends a command via secure mode to z-wave locks."""
        response = self.parent.parent.conn.nodeSecMd(self._id, '1')

        if response is None:
            self.parent.parent.log.warning('ISY could not send command: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY command sent: ' + self._id)
            self.update(_change2update_interval)
            return True

    def unlock(self):
        """ Sends a command via secure mode to z-wave locks."""
        response = self.parent.parent.conn.nodeSecMd(self._id, '0')

        if response is None:
            self.parent.parent.log.warning('ISY could not send command: ' +
                                           self._id)
            return False
        else:
            self.parent.parent.log.info('ISY command sent: ' + self._id)
            self.update(_change2update_interval)
            return True

    def _get_notes(self):
        # Get the device notes, currently only the Spoken property is saved.
        notes_xml = self.parent.parent.conn.getNodeNotes(self._id)
        if notes_xml is None:
            self._spoken = None
        else:
            try:
                notesdom = minidom.parseString(notes_xml)
            except:
                self.parent.log.error('ISY Could not parse node ' + self._id + ' notes '
                                      + 'poorly formatted XML.')
            spoken_tag = notesdom.getElementsByTagName('spoken')
            if spoken_tag and len(spoken_tag) > 0 and spoken_tag[0].firstChild is not None:
                self._spoken = spoken_tag[0].firstChild.toxml()
            else:
                self._spoken = None
        
    def get_groups(self, controller=True, responder=True):
        """
        Returns the groups (scenes) that this node is a member of.
        If controller is True, then the scene it controls is added to the list
        If responder is True, then the scenes it is a responder of are added to the list
        """
        groups = []
        for child in self.parent.parent.nodes.allLowerNodes:
            if child[0] is 'group':
                if responder:
                    if self._id in self.parent.parent.nodes[child[2]].members:
                        groups.append(child[2])
                elif controller:
                    if self._id in self.parent.parent.nodes[child[2]].controllers:
                        groups.append(child[2])
        return groups

    @property
    def spoken(self):
        if self._spoken is False:
            self._get_notes()
        return self._spoken
