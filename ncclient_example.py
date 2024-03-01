from ncclient import manager
from xml.dom import minidom
from netmiko import ConnectHandler
import difflib


class Device:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.__ssh_session = None
        self.__netconf_session = None

    def ssh_connect(self):
        try:
            self.__ssh_session = ConnectHandler(device_type="cisco_xe",
                                                host=self.host,
                                                username=self.username,
                                                password=self.password)
            self.__ssh_session.enable()
        except Exception as e:
            print(e)

    def netconf_connect(self):
        try:
            self.__netconf_session = manager.connect(host=self.host,
                                                     port=830,
                                                     username=self.username,
                                                     password=self.password,
                                                     hostkey_verify=False,
                                                     device_params={'name':'iosxe'})
        except Exception as e:
            print(e)

    def get_xml_config(self):
        c = self.__netconf_session.get_config(source='running').data_xml
        temp = minidom.parseString(c)
        new_xml = temp.toprettyxml()
        with open("base_config.xml", 'w') as f:
            f.write(new_xml)

    def edit_config(self, xml_file):
        self.ssh_connect()
        pre_check = self.show_run()
        with open(xml_file, 'r') as f:
            rpc_config = f.read()
        c = self.__netconf_session.edit_config(rpc_config, target='candidate', default_operation="replace")
        # target='candidate' can be changed to 'running', depends in which mode device is running.
        self.__netconf_session.validate(source="candidate")
        self.__netconf_session.commit()
        print(c)
        post_check = self.show_run()
        with open('config_diff.html', 'w') as diff_file:
            diff = difflib.HtmlDiff()
            diff_file.write(diff.make_file(pre_check, post_check))

    def restore_initial(self, xml_file):
        with open(xml_file, 'r') as f:
            rpc_config = f.read()
        c = self.__netconf_session.edit_config(rpc_config, target='candidate', default_operation="replace")
        self.__netconf_session.commit()
        print(c)

    def show_run(self):
        return self.__ssh_session.send_command('show run').splitlines()


if __name__ == '__main__':
    my_device = Device('<IP>', '<USER>', '<PASS>')
    my_device.netconf_connect()

    # Run this onces to get XML Config into base_config.xml and then comment
    my_device.get_xml_config()

    # Actual Test
    my_device.edit_config('test_config.xml')

    # Restore Initial Config
    my_device.restore_initial('base_config.xml')