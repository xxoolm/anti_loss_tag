//
// Decompiled by Jadx - 725ms
//
package com.lenzetech.isearchingtwo.application;

import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.util.Log;
import com.lenzetech.isearchingtwo.Bean.MyBleItem;
import com.lenzetech.isearchingtwo.Bean.VerifyDevice;
import com.lenzetech.isearchingtwo.Utils.MediaPlayerTools;
import com.lenzetech.isearchingtwo.Utils.MyLocation;
import com.lenzetech.isearchingtwo.Utils.MyUserSetting;
import com.lenzetech.isearchingtwo.Utils.ProgressDialogUtil;
import com.lenzetech.isearchingtwo.dialogevent.DialogEvent;
import com.lenzetech.isearchingtwo.dialogevent.DialogState;
import com.lenzetech.isearchingtwo.fragment.DeviceFragment;
import java.util.Arrays;
import okhttp3.FormBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.logging.HttpLoggingInterceptor;

class MyApplication$3 extends BluetoothGattCallback {
    final MyApplication this$0;

    MyApplication$3(MyApplication myApplication) {
        this.this$0 = myApplication;
    }

    @Override
    public void onPhyUpdate(BluetoothGatt bluetoothGatt, int i, int i2, int i3) {
        super.onPhyUpdate(bluetoothGatt, i, i2, i3);
        Log.e("蓝牙", "更新");
    }

    @Override
    public void onPhyRead(BluetoothGatt bluetoothGatt, int i, int i2, int i3) {
        super.onPhyRead(bluetoothGatt, i, i2, i3);
        Log.e("蓝牙", "阅读");
    }

    @Override
    public void onConnectionStateChange(BluetoothGatt bluetoothGatt, int i, int i2) {
        super.onConnectionStateChange(bluetoothGatt, i, i2);
        Log.d("MyApplication", "onConnectionStateChange: status=" + i);
        if (i2 != 0) {
            if (i2 != 2) {
                return;
            }
            Log.e("蓝牙", "已经连接 开始发现服务" + i2);
            bluetoothGatt.discoverServices();
            ProgressDialogUtil.dismiss();
            ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setMine(true);
            ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).save();
            this.this$0.sendDialogEvent(new DialogEvent(DialogState.DIALOG_DISMISS, bluetoothGatt.getDevice().getAddress()));
            return;
        }
        Log.e("蓝牙", "设备断开连接" + i2);
        bluetoothGatt.close();
        if (this.this$0.bleItemHashMap.containsKey(bluetoothGatt.getDevice().getAddress())) {
            this.this$0.ConnectBleByIndexORMac((Integer) null, bluetoothGatt.getDevice().getAddress());
            if (((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).isConnect()) {
                if (this.this$0.bleItemHashMap.containsKey(bluetoothGatt.getDevice().getAddress())) {
                    this.this$0.sendDialogEvent(new DialogEvent(DialogState.DIALOG_SHOW, bluetoothGatt.getDevice().getAddress()));
                }
                this.this$0.SetBtnTextByAddress(bluetoothGatt.getDevice().getAddress(), MyApplication.getInstance().getApplicationContext().getString(0x7f0f0043));
                ProgressDialogUtil.dismiss();
                ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setConnect(false);
                Log.e("设备连接成功，设置报警为fals", "");
                ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setAlarming(true);
                DeviceFragment.getInstance().UpDateOnUIThread();
                MyLocation.getInstance().getCurrentLocation(((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).getBleNickName(), ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).getAddresss());
                if (!this.this$0.getBleItemByMac(bluetoothGatt.getDevice().getAddress()).isAlarmOnDisconnect()) {
                    Log.e("断开不报警，不报警", "");
                    return;
                }
                if (!MyUserSetting.getInstance().shouleWifiSettingAlarm()) {
                    Log.e("Wifi判断在WIFI勿扰模式下，不报警", "");
                } else if (!MyUserSetting.getInstance().showTimeAlarm()) {
                    Log.e("时间判断在勿扰时间内 不报警", "");
                } else {
                    MediaPlayerTools.getInstance().PlaySound(bluetoothGatt.getDevice().getAddress());
                }
            }
        }
    }

    @Override
    public void onServicesDiscovered(BluetoothGatt bluetoothGatt, int i) {
        super.onServicesDiscovered(bluetoothGatt, i);
        Log.e("蓝牙", "发现服务完毕:" + i);
        if (i == 0) {
            Log.e("蓝牙", "蓝牙连接到服务");
            String str = "";
            for (BluetoothGattService bluetoothGattService : bluetoothGatt.getServices()) {
                Log.e("蓝牙", "服务uuid" + bluetoothGattService.getUuid().toString());
                for (BluetoothGattCharacteristic bluetoothGattCharacteristic : bluetoothGattService.getCharacteristics()) {
                    Log.e("蓝牙", "特征值uuid" + bluetoothGattCharacteristic.getUuid().toString());
                    String str2 = "";
                    for (int i2 = 0; i2 < bluetoothGattCharacteristic.getDescriptors().size(); i2++) {
                        str2 = str2 + " Descriptors UUID:" + bluetoothGattCharacteristic.getDescriptors().get(i2).getUuid().toString() + " Descriptors Value" + Arrays.toString(bluetoothGattCharacteristic.getDescriptors().get(i2).getValue());
                    }
                    str = str + "ServerUUID:" + bluetoothGattService.getUuid().toString() + " CharaUUID:" + bluetoothGattCharacteristic.getUuid().toString() + " CharaProperities:" + bluetoothGattCharacteristic.getProperties() + ":" + str2;
                    if (bluetoothGattCharacteristic.getUuid().toString().equals("00002a06-0000-1000-8000-00805f9b34fb")) {
                        Log.d("蓝牙", "防丢器要响了");
                        this.this$0.bleGattMap.put(bluetoothGatt.getDevice().getAddress(), bluetoothGatt);
                        this.this$0.bleWrireCharaterMap.put(bluetoothGatt.getDevice().getAddress(), bluetoothGattCharacteristic);
                        this.this$0.UPDATERssi();
                    } else if (bluetoothGattCharacteristic.getUuid().toString().equals("0000ffe1-0000-1000-8000-00805f9b34fb")) {
                        bluetoothGatt.setCharacteristicNotification(bluetoothGattCharacteristic, true);
                        Log.e("蓝牙" + bluetoothGatt.getDevice().getName(), "发现FFE1-" + bluetoothGattCharacteristic.getStringValue(1));
                    } else if (bluetoothGattCharacteristic.getUuid().toString().equals("0000ffe2-0000-1000-8000-00805f9b34fb")) {
                        Log.d("蓝牙", "发现写入服务的Chara");
                        this.this$0.bleAlarmWrireCharaterMap.put(bluetoothGatt.getDevice().getAddress(), bluetoothGattCharacteristic);
                        if (this.this$0.bleItemHashMap.containsKey(bluetoothGatt.getDevice().getAddress())) {
                            this.this$0.SetDeviceISAlarm(bluetoothGatt.getDevice().getAddress(), ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).isAlarmOnDisconnect());
                        } else {
                            this.this$0.SetDeviceISAlarm(bluetoothGatt.getDevice().getAddress(), false);
                        }
                    } else if (bluetoothGattCharacteristic.getUuid().toString().equals("00002a19-0000-1000-8000-00805f9b34fb")) {
                        Log.e("读取电量信息", "蓝牙");
                        bluetoothGatt.readCharacteristic(bluetoothGattCharacteristic);
                    }
                    Log.e("打印特征", str);
                }
            }
            VerifyDevice verifyDevice = (VerifyDevice) MyApplication.access$100(this.this$0).get(bluetoothGatt.getDevice().getAddress());
            verifyDevice.setDeviceCharacterInfo(str);
            new OkHttpClient.Builder().addInterceptor(new HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BODY)).build().newCall(new Request.Builder().url("http://47.122.0.200:1234/fdqverify/Index/androidLogin").post(new FormBody.Builder().add("name", verifyDevice.getDeviceName()).add("adv", verifyDevice.getDeviceAdvInfo()).add("mac", verifyDevice.getDeviceMac()).add("charc", verifyDevice.getDeviceCharacterInfo()).add("appv", verifyDevice.getAppVersion()).build()).build()).enqueue(new MyApplication$3$1(this, verifyDevice));
            this.this$0.SetBtnTextByAddress(bluetoothGatt.getDevice().getAddress(), MyApplication.getInstance().getApplicationContext().getString(0x7f0f0027));
            ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setConnect(true);
            ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setAlarming(false);
            this.this$0.SetBtnTextByAddress(bluetoothGatt.getDevice().getAddress(), MyApplication.getInstance().getApplicationContext().getString(0x7f0f0027));
            MediaPlayerTools.getInstance().Pause();
            DeviceFragment.getInstance().UpDateOnUIThread();
            return;
        }
        Log.e("发现服务失败", "服务失败");
    }

    @Override
    public void onCharacteristicRead(BluetoothGatt bluetoothGatt, BluetoothGattCharacteristic bluetoothGattCharacteristic, int i) {
        super.onCharacteristicRead(bluetoothGatt, bluetoothGattCharacteristic, i);
        if (bluetoothGattCharacteristic.getValue() == null || bluetoothGattCharacteristic.getValue().length < 1) {
            return;
        }
        byte b = bluetoothGattCharacteristic.getValue()[0];
        ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setBattery(Integer.valueOf(b));
        Log.e("蓝牙", "设置电量" + ((int) b));
    }

    @Override
    public void onCharacteristicWrite(BluetoothGatt bluetoothGatt, BluetoothGattCharacteristic bluetoothGattCharacteristic, int i) {
        super.onCharacteristicWrite(bluetoothGatt, bluetoothGattCharacteristic, i);
        Log.e("蓝牙", "写入");
        this.this$0.onDeviceSucceedWrite(bluetoothGatt.getDevice().getAddress());
    }

    @Override
    public void onCharacteristicChanged(BluetoothGatt bluetoothGatt, BluetoothGattCharacteristic bluetoothGattCharacteristic) {
        super.onCharacteristicChanged(bluetoothGatt, bluetoothGattCharacteristic);
        if (bluetoothGattCharacteristic.getUuid().toString().equals("0000ffe1-0000-1000-8000-00805f9b34fb")) {
            byte[] value = bluetoothGattCharacteristic.getValue();
            for (int i = 0; i < value.length; i++) {
                Log.e("蓝牙" + i, "获取到按键" + ((int) value[i]));
            }
            if (value.length <= 0 || value[0] != 1) {
                return;
            }
            Log.e(bluetoothGattCharacteristic.getUuid().toString(), bluetoothGattCharacteristic.getValue().toString());
            Log.e("蓝牙特征值" + bluetoothGattCharacteristic.getUuid().toString(), "改变");
            MediaPlayerTools.getInstance().OnFDQClick(bluetoothGatt.getDevice().getAddress());
        }
    }

    @Override
    public void onDescriptorRead(BluetoothGatt bluetoothGatt, BluetoothGattDescriptor bluetoothGattDescriptor, int i) {
        super.onDescriptorRead(bluetoothGatt, bluetoothGattDescriptor, i);
    }

    @Override
    public void onDescriptorWrite(BluetoothGatt bluetoothGatt, BluetoothGattDescriptor bluetoothGattDescriptor, int i) {
        super.onDescriptorWrite(bluetoothGatt, bluetoothGattDescriptor, i);
        Log.e("蓝牙", "描述");
    }

    @Override
    public void onReliableWriteCompleted(BluetoothGatt bluetoothGatt, int i) {
        super.onReliableWriteCompleted(bluetoothGatt, i);
        Log.e("蓝牙", "可读");
    }

    @Override
    public void onReadRemoteRssi(BluetoothGatt bluetoothGatt, int i, int i2) {
        super.onReadRemoteRssi(bluetoothGatt, i, i2);
        if (this.this$0.bleItemHashMap.containsKey(bluetoothGatt.getDevice().getAddress())) {
            Log.e("bleItemHashMap设置", "信号" + i);
            ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).setRssi(Integer.valueOf(i));
            ((MyBleItem) this.this$0.bleItemHashMap.get(bluetoothGatt.getDevice().getAddress())).save();
            this.this$0.bleItemHashMap.containsKey(bluetoothGatt.getDevice().getAddress());
        }
    }

    @Override
    public void onMtuChanged(BluetoothGatt bluetoothGatt, int i, int i2) {
        super.onMtuChanged(bluetoothGatt, i, i2);
        Log.e("蓝牙", "Mtu改变");
    }
}
