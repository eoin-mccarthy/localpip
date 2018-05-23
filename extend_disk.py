#!/usr/bin/env python

from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl
import sys

args = sys.argv

if len(args) < 7:
    print "Usage: %s vcenter-host vc-user vc-password ip-address disk new-size" % args[0]
    sys.exit(1)

vcenter = args[1]
vcuser = args[2]
vcpass = args[3]
ipAddress = args[4]
diskname = args[5]
newsize = args[6]

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

def extendDisk(dev, vm, capacity_kb, datastore_freespace_kb, new_capacity_gb):

    new_capacity_kb = new_capacity_gb * 1024 * 1024
    if new_capacity_kb <= capacity_kb:
         print "New size must be larger than existing size"
         return 1
    extra_capacity_kb = new_capacity_kb - capacity_kb
    if extra_capacity_kb > datastore_freespace_kb:
         print "Not enough capacity on datastore: free space is %s KB and you need %s KB" % (datastore_freespace_kb, extra_capacity_kb)
         return 1
    dev_changes = []
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.key = dev.key
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.fileName = dev.backing.fileName
    disk_spec.device.backing.diskMode = dev.backing.diskMode
    disk_spec.device.controllerKey = dev.controllerKey
    disk_spec.device.unitNumber = dev.unitNumber
    disk_spec.device.capacityInKB = new_capacity_kb
    dev_changes.append(disk_spec)

    spec = vim.vm.ConfigSpec()
    spec.deviceChange = dev_changes

    task = vm.ReconfigVM_Task(spec=spec)

    print "Disk resized"

si = connect.SmartConnect(host=vcenter, user=vcuser, pwd=vcpass)
content = si.RetrieveContent()

all_datastores = get_all_objs(content, [vim.Datastore])

searchIndex = content.searchIndex
vms = searchIndex.FindAllByIp(ip=ipAddress, vmSearch=True)

vm = vms[0]
print vm.name
found_disk = False
for dev in vm.config.hardware.device:
    if isinstance(dev, vim.vm.device.VirtualDisk):
        if dev.deviceInfo.label == diskname:
            found_disk = True
            datastore = dev.backing.datastore
            datastore_freespace_kb = get_free_space(datastore, all_datastores) / 1024
            capacity_in_kb = dev.capacityInKB
            extendDisk(dev,vm,capacity_in_kb,datastore_freespace_kb,newsize)
            break

if not found_disk:
    print "Could not find disk named %s on vm %s" % (diskname, vm.name)

