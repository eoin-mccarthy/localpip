#!/usr/bin/env python

from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl
import sys

args = sys.argv

if len(args) < 5:
    print "Usage: %s vcenter-host vc-user vc-password ip-address" % args[0]
    sys.exit(1)

vcenter = args[1]
vcuser = args[2]
vcpass = args[3]
ipAddress = args[4]

def get_all_objs(content, vimtype):
    obj = {}
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for managed_object_ref in container.view:
        obj.update({managed_object_ref: managed_object_ref.name})
    return obj

def get_free_space(datastore, all_ds):
    for ds in all_ds:
        if ds == datastore:
            return int(ds.info.freeSpace)

def get_name(datastore, all_ds):
    for ds in all_ds:
        if ds == datastore:
            return ds.name

def get_vm_datastores(vm):
    datastores = {}
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk):
            datastore = dev.backing.datastore
            diskname = dev.deviceInfo.label
            datastores[diskname] = {}
            datastores[diskname]['datastore'] = get_name(datastore, all_datastores)
            datastores[diskname]['size'] = int(dev.capacityInKB) / 1024 / 1024
            datastores[diskname]['datastore_freespace'] = get_free_space(datastore, all_datastores) / 1024 / 1024
    return datastores

si = connect.SmartConnect(host=vcenter, user=vcuser, pwd=vcpass)
content = si.RetrieveContent()

all_datastores = get_all_objs(content, [vim.Datastore])

searchIndex = content.searchIndex
vms = searchIndex.FindAllByIp(ip=ipAddress, vmSearch=True)

vm = vms[0]
print vm.name, ipAddress
disk_info = get_vm_datastores(vm)

disks = disk_info.keys()
disks.sort()
for disk in disks:
    print "---------------------------------------------"
    print disk
    print "---------------------------------------------"
    print "Datastore: %s" % disk_info[disk]['datastore']
    print "Datastore free space: %s MB" % disk_info[disk]['datastore_freespace']
    print "Disk size: %s GB" % disk_info[disk]['size']
    print ""

