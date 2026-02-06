//
// Decompiled by Jadx - 678ms
//
package com.lenzetech.isearchingtwo.application;

import android.app.Application;
import android.app.Dialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Build;
import android.os.Handler;
import android.os.ParcelUuid;
import android.util.Log;
import android.widget.TextView;
import android.widget.Toast;
import androidx.fragment.app.FragmentActivity;
import com.blankj.utilcode.util.ActivityUtils;
import com.blankj.utilcode.util.Utils;
import com.jianjin.camera.CustomCameraAgent;
import com.lenzetech.isearchingtwo.Bean.MyBleItem;
import com.lenzetech.isearchingtwo.Bean.VerifyDevice;
import com.lenzetech.isearchingtwo.BluetoothMonitorReceiver;
import com.lenzetech.isearchingtwo.MyService;
import com.lenzetech.isearchingtwo.Utils.CustomDialog;
import com.lenzetech.isearchingtwo.Utils.MediaPlayerTools;
import com.lenzetech.isearchingtwo.Utils.MyUserSetting;
import com.lenzetech.isearchingtwo.activity.DeviceActivity.BleSettingActivity;
import com.lenzetech.isearchingtwo.application.MyApplication$;
import com.lenzetech.isearchingtwo.dialogevent.DialogEvent;
import com.lenzetech.isearchingtwo.dialogevent.DialogState;
import com.lenzetech.isearchingtwo.dialogevent.EventCallback;
import com.lenzetech.isearchingtwo.fragment.DeviceFragment;
import com.lenzetech.isearchingtwo.permission.BlePermissionHelper;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.regex.Pattern;
import org.litepal.LitePal;

public class MyApplication extends Application implements EventCallback {
    private static final String TAG = "MyApplication";
    private static MyApplication myApplication;
    public BlePermissionHelper blePermissionHelper;
    private BluetoothMonitorReceiver bluetoothMonitorReceiver;
    private FragmentActivity context;
    TextView dialog_new_message;
    TextView dialog_new_session;
    BluetoothAdapter mBluetoothAdapter;
    private Dialog mDialog;
    private Dialog mDialog2;
    private EventCallback mEventCallback;
    private Handler mHandler;
    MediaPlayerTools mediaPlayerTools;
    private HashMap<String, DialogInterface> mHashMap = new HashMap<>();
    private HashMap<String, VerifyDevice> verifyDic = new HashMap<>();
    public HashMap<String, MyBleItem> bleItemHashMap = new HashMap<>();
    public HashMap<String, BluetoothDevice> bleDeviceMap = new HashMap<>();
    public HashMap<String, BluetoothGattCharacteristic> bleWrireCharaterMap = new HashMap<>();
    public HashMap<String, BluetoothGatt> bleGattMap = new HashMap<>();
    public HashMap<String, Integer> reConnectCountMap = new HashMap<>();
    public HashMap<String, BluetoothGattCharacteristic> bleAlarmWrireCharaterMap = new HashMap<>();
    private BluetoothLeScanner mLeScanner = null;
    private ScanCallback scanCallbackH = new MyApplication$2(this);
    BluetoothStateReceiver mBluetoothStateReceiver = new BluetoothStateReceiver(this, (MyApplication$1) null);
    private MyBleItem myBleItem = null;

    @Override
    public void onCreate() {
        super.onCreate();
        Utils.init(this);
        setEventCallbackZ(this);
        LitePal.initialize(this);
        MyUserSetting.getInstance().InitUserSetting();
        myApplication = this;
        this.mHandler = new MyApplication$1(this, getMainLooper());
        Log.e("MyApplication代码启动了！", "MyApplication代码启动了！");
        CustomCameraAgent.init(this);
        LoadFromDisk();
        if (Build.VERSION.SDK_INT < 26) {
            startService(new Intent(this, (Class<?>) MyService.class));
        }
        this.bluetoothMonitorReceiver = new BluetoothMonitorReceiver();
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction("android.bluetooth.adapter.action.STATE_CHANGED");
        registerReceiver(this.bluetoothMonitorReceiver, intentFilter);
    }

    public void initByCloseBl() {
        this.bleItemHashMap = new HashMap<>();
        this.bleDeviceMap = new HashMap<>();
        this.bleWrireCharaterMap = new HashMap<>();
        this.bleGattMap = new HashMap<>();
        this.bleAlarmWrireCharaterMap = new HashMap<>();
        LoadFromDisk();
    }

    public void LoadFromDisk() {
        List findAll = LitePal.findAll(MyBleItem.class, new long[0]);
        Log.e("LoadFromDisk从本地开始加载设备", findAll.size() + "");
        for (int i = 0; i < findAll.size(); i++) {
            if (this.bleItemHashMap.containsKey(((MyBleItem) findAll.get(i)).getAddresss())) {
                Log.e("LoadFromDisk", i + "设备列表中存在");
            } else {
                Log.e("LoadFromDisk", i + "设备列表中不存在，添加到显示列表");
                this.bleItemHashMap.put(((MyBleItem) findAll.get(i)).getAddresss(), (MyBleItem) findAll.get(i));
                this.reConnectCountMap.put(((MyBleItem) findAll.get(i)).getAddresss(), 5);
                MyBleItem myBleItem = this.bleItemHashMap.get(((MyBleItem) findAll.get(i)).getAddresss());
                myBleItem.setBtnShowText(getString(0x7f0f0098));
                myBleItem.setConnect(false);
                myBleItem.setMine(true);
            }
            DeviceFragment.getInstance().UpDateOnUIThread();
        }
    }

    public static MyApplication getInstance() {
        return myApplication;
    }

    public void InitBle(FragmentActivity fragmentActivity) {
        this.context = fragmentActivity;
        BlePermissionHelper blePermissionHelper = new BlePermissionHelper(fragmentActivity);
        this.blePermissionHelper = blePermissionHelper;
        if (!blePermissionHelper.isSupportBLE()) {
            Toast.makeText((Context) fragmentActivity, 0x7f0f005b, 1).show();
            return;
        }
        BluetoothAdapter adapter = ((BluetoothManager) fragmentActivity.getApplicationContext().getSystemService("bluetooth")).getAdapter();
        this.mBluetoothAdapter = adapter;
        this.mLeScanner = adapter.getBluetoothLeScanner();
        if (this.mBluetoothAdapter.isEnabled()) {
            Log.e("蓝牙", "设备开启蓝牙");
            startDiscovery();
        } else {
            Log.e("蓝牙", "设备没有开启蓝牙");
            this.blePermissionHelper.checkNOpenBl();
        }
    }

    public void ChangeBLeItemSetting(String str, String str2, Boolean bool, Integer num, byte[] bArr) {
        Log.e("修改", "开始修改设备设置");
        MyBleItem myBleItem = this.bleItemHashMap.get(str);
        if (this.bleItemHashMap.keySet().contains(str)) {
            Log.e("修改成功，获取到设备", "222");
        } else {
            Log.e("修改失败，设备为空", "333");
        }
        if (str2 != null) {
            myBleItem.setBleNickName(str2);
            myBleItem.save();
        }
        if (bArr != null) {
            myBleItem.setImageByte(bArr);
            myBleItem.save();
        }
        if (bool != null) {
            myBleItem.setAlarmOnDisconnect(bool.booleanValue());
            myBleItem.save();
        }
        if (num != null) {
            myBleItem.setRingIndex(num);
            myBleItem.save();
        }
        DeviceFragment.getInstance().UpDateOnUIThread();
    }

    public static String getVersionName(Context context) {
        try {
            return context.getPackageManager().getPackageInfo(context.getPackageName(), 0).versionName;
        } catch (PackageManager.NameNotFoundException e) {
            e.printStackTrace();
            return null;
        }
    }

    public static String bytesToHex(byte[] bArr) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bArr) {
            String hexString = Integer.toHexString(b & 255);
            if (hexString.length() == 1) {
                sb.append('0');
            }
            sb.append(hexString);
        }
        return sb.toString();
    }

    public void startDiscovery() {
        if (!this.blePermissionHelper.checkNOpenGps() || !this.blePermissionHelper.checkNOpenBl()) {
            Log.e(TAG, "scan fail");
            return;
        }
        if (this.mBluetoothAdapter == null) {
            Log.e("蓝牙", "蓝牙搜索失败");
            return;
        }
        Log.e("蓝牙", "开始搜索蓝牙");
        if (this.mBluetoothAdapter.isDiscovering()) {
            return;
        }
        if (this.bleItemHashMap.size() > 0) {
            ArrayList arrayList = new ArrayList(this.bleItemHashMap.keySet());
            for (int i = 0; i < arrayList.size(); i++) {
                if (!this.bleItemHashMap.get(arrayList.get(i)).isMine()) {
                    this.bleItemHashMap.remove(arrayList.get(i));
                }
            }
        }
        DeviceFragment.getInstance().UpDateOnUIThread();
        if (this.mBluetoothAdapter.isEnabled()) {
            Log.e("蓝牙", "开始扫描");
            ArrayList arrayList2 = new ArrayList();
            ScanFilter.Builder builder = new ScanFilter.Builder();
            builder.setServiceUuid(ParcelUuid.fromString("0000ffe0-0000-1000-8000-00805f9b34fb"));
            ScanFilter build = builder.build();
            arrayList2.add(build);
            ScanSettings.Builder builder2 = new ScanSettings.Builder();
            builder2.setScanMode(2);
            if (Build.VERSION.SDK_INT >= 23) {
                builder2.setMatchMode(1);
            }
            if (Build.VERSION.SDK_INT >= 23) {
                builder2.setCallbackType(1);
            }
            if (Build.VERSION.SDK_INT >= 26) {
                builder2.setLegacy(true);
            }
            new Handler().postDelayed(new MyApplication$.ExternalSyntheticLambda1(this, build, builder2.build()), 200L);
            Log.e("扫描", "扫描一段时间后停止");
            new Handler().postDelayed(new MyApplication$.ExternalSyntheticLambda0(this), 5000L);
        }
    }

    void lambda$startDiscovery$0$com-lenzetech-isearchingtwo-application-MyApplication(ScanFilter scanFilter, ScanSettings scanSettings) {
        Log.e("蓝牙", "开始扫描");
        if (this.mLeScanner == null) {
            this.mLeScanner = this.mBluetoothAdapter.getBluetoothLeScanner();
        }
        this.mLeScanner.startScan(Collections.singletonList(scanFilter), scanSettings, this.scanCallbackH);
    }

    void lambda$startDiscovery$1$com-lenzetech-isearchingtwo-application-MyApplication() {
        Log.e("蓝牙", "停止扫描");
        this.mLeScanner.stopScan(this.scanCallbackH);
    }

    public void OnMyDeviceFound(BluetoothDevice bluetoothDevice, Boolean bool) {
        this.bleDeviceMap.put(bluetoothDevice.getAddress(), bluetoothDevice);
        if (this.bleItemHashMap.containsKey(bluetoothDevice.getAddress())) {
            if (this.bleItemHashMap.get(bluetoothDevice.getAddress()).getBtnShowText().equals(getString(0x7f0f0098))) {
                this.bleItemHashMap.get(bluetoothDevice.getAddress()).setBtnShowText(getString(0x7f0f0026));
                if (this.bleItemHashMap.get(bluetoothDevice.getAddress()).isMine()) {
                    Log.e("发现我们的设备，", "连接到我的设备");
                    ConnectBleByIndexORMac(null, bluetoothDevice.getAddress());
                    this.bleItemHashMap.get(bluetoothDevice.getAddress()).setBtnShowText(getString(0x7f0f003b));
                } else {
                    Log.e("发现我们的设222备，", "连接到我的222设备");
                }
                DeviceFragment.getInstance().UpDateOnUIThread();
                Log.e("刷新设备1", "设备存在");
                return;
            }
            Log.e("刷新设备2", this.bleItemHashMap.get(bluetoothDevice.getAddress()).getBtnShowText());
            return;
        }
        if (this.bleItemHashMap.size() >= 8) {
            return;
        }
        MyBleItem myBleItem = new MyBleItem();
        String trim = Pattern.compile(" [\n`~!@#$%^&*()+=|{}':;',\\[\\].<>/?~！@#￥%……&*（）——+|{}【】‘；：”“’。， 、？] 0").matcher(bluetoothDevice.getName()).replaceAll(" ").trim();
        myBleItem.setBleNickName(trim);
        Log.d(TAG, "OnMyDeviceFound123: " + trim);
        myBleItem.setAddresss(bluetoothDevice.getAddress());
        myBleItem.setBtnShowText(getString(0x7f0f0098));
        myBleItem.setImageByte((byte[]) null);
        if (bool.booleanValue()) {
            myBleItem.setHasBattery(bool);
        }
        this.bleItemHashMap.put(bluetoothDevice.getAddress(), myBleItem);
        DeviceFragment.getInstance().UpDateOnUIThread();
    }

    public MyBleItem getBleItemByid(Integer num) {
        return (MyBleItem) this.bleItemHashMap.values().toArray()[num.intValue()];
    }

    public void setBtnTextById(Integer num, String str) {
        ((MyBleItem) this.bleItemHashMap.values().toArray()[num.intValue()]).setBtnShowText(str);
        DeviceFragment.getInstance().UpDateOnUIThread();
    }

    public void SetBtnTextByAddress(String str, String str2) {
        this.bleItemHashMap.get(str).setBtnShowText(str2);
        DeviceFragment.getInstance().UpDateOnUIThread();
    }

    public void onDeviceSucceedWrite(String str) {
        String btnShowText = this.bleItemHashMap.get(str).getBtnShowText();
        if (btnShowText.equals(getString(0x7f0f0023))) {
            this.bleItemHashMap.get(str).setBtnShowText(getString(0x7f0f0027));
        } else if (btnShowText.equals(getString(0x7f0f0027))) {
            this.bleItemHashMap.get(str).setBtnShowText(getString(0x7f0f0023));
        }
        DeviceFragment.getInstance().UpDateOnUIThread();
    }

    public void AlarmByAddress(String str) {
        Log.e("开始报警1", "开始报警" + str);
        if (this.bleGattMap.containsKey(str) && this.bleGattMap.containsKey(str)) {
            Log.e("开始报警2", "开始报警" + str);
            Log.e("开始报警4", "开始报警" + str);
            this.bleWrireCharaterMap.get(str).setValue(new byte[]{1});
            Log.e("开始报警5", "开始报警" + str);
            this.bleGattMap.get(str).writeCharacteristic(this.bleWrireCharaterMap.get(str));
            return;
        }
        Log.e("开始报警3", "开始报警" + str);
    }

    public void CancleAlarmByAddress(String str) {
        Log.e("开始报警1", "开始报警" + str);
        if (this.bleGattMap.containsKey(str)) {
            Log.e("开始报警2", "开始报警" + str);
            Log.e("开始报警4", "开始报警" + str);
            this.bleWrireCharaterMap.get(str).setValue(new byte[]{0});
            Log.e("开始报警5", "开始报警" + str);
            this.bleGattMap.get(str).writeCharacteristic(this.bleWrireCharaterMap.get(str));
            return;
        }
        Log.e("开始报警3", "开始报警" + str);
    }

    public void SetDeviceISAlarm(String str, boolean z) {
        Log.e("设置断开是否报警", "设置断开是否报警" + str);
        if (!this.bleAlarmWrireCharaterMap.containsKey(str)) {
            Log.e("设置断开是否报警", "设置断开是否报警" + str);
            return;
        }
        Log.e("设置断开是否报警", "设置断开是否报警" + str);
        if (z) {
            Log.e("设置断开是否报警:断开报警", "设置断开是否报警" + str);
            this.bleAlarmWrireCharaterMap.get(str).setValue(new byte[]{1});
        } else {
            Log.e("设置断开是否报警:不报警", "设置断开是否报警" + str);
            this.bleAlarmWrireCharaterMap.get(str).setValue(new byte[]{0});
        }
        Log.e("设置断开是否报警", "设置断开是否报警OK" + str);
        if (this.bleGattMap.containsKey(str)) {
            this.bleGattMap.get(str).writeCharacteristic(this.bleAlarmWrireCharaterMap.get(str));
        }
    }

    public void SetIsAlarmingByMac(String str, Boolean bool) {
        if (str == null || !this.bleItemHashMap.containsKey(str)) {
            return;
        }
        this.bleItemHashMap.get(str).setAlarming(bool.booleanValue());
    }

    public void OnItemSettingClick(String str) {
        if (str == null) {
            Log.e("蓝牙", "mac地址为空，不进行设置" + str);
            return;
        }
        if (this.bleItemHashMap.containsKey(str) && this.bleItemHashMap.get(str).isConnect()) {
            Intent intent = new Intent(getApplicationContext(), (Class<?>) BleSettingActivity.class);
            intent.putExtra("mac", str);
            intent.addFlags(0x10000000);
            startActivity(intent);
        }
    }

    public MyBleItem getBleItemByMac(String str) {
        return this.bleItemHashMap.get(str);
    }

    public void deleteItemByMac(String str) {
        this.bleItemHashMap.get(str).delete();
        this.bleItemHashMap.remove(str);
        if (this.bleGattMap.containsKey(str)) {
            this.bleGattMap.get(str).disconnect();
            this.bleGattMap.remove(str);
        }
        LoadFromDisk();
        DeviceFragment.getInstance().UpDateOnUIThread();
    }

    public void ConnectBleByIndexORMac(Integer num, String str) {
        BluetoothDevice bluetoothDevice;
        if (num != null) {
            Log.e("蓝牙bluetoothDevice1", "更新bluetoothDevice");
            bluetoothDevice = this.bleDeviceMap.get(((MyBleItem) this.bleItemHashMap.values().toArray()[num.intValue()]).getAddresss());
            if (bluetoothDevice != null) {
                this.reConnectCountMap.put(bluetoothDevice.getAddress(), 5);
            }
        } else if (str != null) {
            Log.e("蓝牙bluetoothDevice2", "更新bluetoothDevice");
            this.bleItemHashMap.get(str);
            bluetoothDevice = this.bleDeviceMap.get(str);
        } else {
            bluetoothDevice = null;
        }
        if (bluetoothDevice == null) {
            Log.e("蓝牙bluetoothDevice3", "更新bluetoothDevice");
        } else {
            Log.e("蓝牙bluetoothDevice", "更新bluetoothDevice");
            bluetoothDevice.connectGatt(getApplicationContext(), false, new MyApplication$3(this));
        }
    }

    public boolean isWifi() {
        NetworkInfo activeNetworkInfo = ((ConnectivityManager) getApplicationContext().getSystemService("connectivity")).getActiveNetworkInfo();
        return activeNetworkInfo != null && activeNetworkInfo.getType() == 1;
    }

    public void UPDATERssi() {
        for (String str : this.bleGattMap.keySet()) {
            Log.e(str, "设备信息");
            this.bleGattMap.get(str).readRemoteRssi();
            DeviceFragment.getInstance().UpDateOnUIThread();
        }
    }

    public void setEventCallbackZ(EventCallback eventCallback) {
        this.mEventCallback = eventCallback;
    }

    private void registerReceiver() {
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction("android.bluetooth.adapter.action.STATE_CHANGED");
        registerReceiver(this.mBluetoothStateReceiver, intentFilter);
    }

    private void unregisterReceiver() {
        unregisterReceiver(this.mBluetoothStateReceiver);
    }

    public void sendDialogEvent(DialogEvent dialogEvent) {
        this.mHandler.post(new MyApplication$4(this, dialogEvent));
    }

    public void onEvent(DialogEvent dialogEvent) {
        if (dialogEvent.getmDialogState() == DialogState.DIALOG_DISMISS) {
            Log.d(TAG, "onEvent: DialogState.DIALOG_DISMISS");
            if (dialogEvent.isDoubleClick()) {
                Dialog dialog = this.mDialog2;
                if (dialog != null) {
                    dialog.dismiss();
                    this.mDialog2 = null;
                    return;
                }
                return;
            }
            Dialog dialog2 = this.mDialog;
            if (dialog2 != null) {
                dialog2.dismiss();
                this.mDialog = null;
                return;
            }
            return;
        }
        if (dialogEvent.getmDialogState() == DialogState.DIALOG_SHOW) {
            if (dialogEvent.isDoubleClick()) {
                if (this.mDialog2 == null) {
                    this.mDialog2 = dialogbledoubleclick(dialogEvent.getAddress());
                } else {
                    Log.d(TAG, "onEvent: mDialog2不做处理");
                }
            } else if (this.mDialog == null) {
                this.mDialog = dialogbleconnect(dialogEvent.getAddress());
            } else {
                Log.d(TAG, "onEvent: 不做处理");
            }
            Log.d(TAG, "onEvent: DialogState.DIALOG_SHOW ");
        }
    }

    public Dialog dialogbleconnect(String str) {
        String format = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss ").format(new Date(System.currentTimeMillis()));
        CustomDialog build = new CustomDialog.Builder(ActivityUtils.getTopActivity()).style(0x7f1000cd).cancelTouchout(false).widthdp(300).heightdp(430).view(0x7f0b0038).build();
        build.addViewOnclick(0x7f080079, new MyApplication$5(this, build));
        build.show();
        build.setCancelable(false);
        String bleNickName = this.bleItemHashMap.containsKey(str) ? this.bleItemHashMap.get(str).getBleNickName() : "iTAG";
        TextView textView = (TextView) build.findViewById(0x7f08007e);
        this.dialog_new_session = textView;
        textView.setText(bleNickName + " " + getString(0x7f0f0040));
        TextView textView2 = (TextView) build.findViewById(0x7f08007d);
        this.dialog_new_message = textView2;
        textView2.setText(format);
        return build;
    }

    public Dialog dialogbledoubleclick(String str) {
        String format = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss ").format(new Date(System.currentTimeMillis()));
        CustomDialog build = new CustomDialog.Builder(ActivityUtils.getTopActivity()).style(0x7f1000cd).cancelTouchout(false).widthdp(300).heightdp(430).view(0x7f0b0038).build();
        build.addViewOnclick(0x7f080079, new MyApplication$6(this, build));
        build.show();
        build.setCancelable(false);
        String bleNickName = this.bleItemHashMap.containsKey(str) ? this.bleItemHashMap.get(str).getBleNickName() : "iTAG";
        TextView textView = (TextView) build.findViewById(0x7f08007e);
        this.dialog_new_session = textView;
        textView.setText(bleNickName + " " + getString(0x7f0f0041));
        TextView textView2 = (TextView) build.findViewById(0x7f08007d);
        this.dialog_new_message = textView2;
        textView2.setText(format);
        return build;
    }
}
