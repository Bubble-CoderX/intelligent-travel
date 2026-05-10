export function getDeviceId(): string {
  let deviceId = localStorage.getItem('travelmate_device_id')
  if (!deviceId) {
    deviceId = 'dev_' + crypto.randomUUID()
    localStorage.setItem('travelmate_device_id', deviceId)
  }
  return deviceId
}
