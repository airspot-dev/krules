# on-data-received
When data are received it is mainly managed the device status
setting a lastSeen property and reacting to them as well as
other property changes

It also responds to scheduled event requesting for switch status to INACTIVE

the event is scheduled (and re-scheduled) each time we attempt to set status to ACTIVE
(even if it already is)