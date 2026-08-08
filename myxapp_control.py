import src.e2ap_xapp as e2ap_xapp
from ran_messages_pb2 import *
from time import sleep
from ricxappframe.e2ap.asn1 import IndicationMsg

def xappLogic():

    # instanciate xapp 
    connector = e2ap_xapp.e2apXapp()

    # get gnbs connected to RIC
    gnb_id_list = connector.get_gnb_id_list()
    print("{} gNB connected to RIC, listing:".format(len(gnb_id_list)))
    for gnb_id in gnb_id_list:
        print(gnb_id)
    print("---------")

    gnb = gnb_id_list[0]
    report_request_buffer = e2sm_report_request_buffer()
    while True:
        print("Sending report request")
        connector.send_e2ap_control_request(report_request_buffer,gnb)
        print("Sleeping for 1 second, so we are sure we receive the answer")
        sleep(1)
        messgs = connector.get_queued_rx_message()
        if len(messgs) == 0:
            print("no messages received")
            print("____")
        else:
            print("{} messages received while waiting, printing:".format(len(messgs)))
            for msg in messgs:
                if msg["message type"] == connector.RIC_IND_RMR_ID:
                    print("RIC Indication received from gNB {}, decoding E2SM payload".format(msg["meid"]))
                    indm = IndicationMsg()
                    indm.decode(msg["payload"])
                    resp = RAN_indication_response()
                    resp.ParseFromString(indm.indication_message)
                    print(resp)
                    print("___")
                else:
                    print("Unrecognized E2AP message received from gNB {}".format(msg["meid"]))

        # now we ask for data to the human
        rnti = input("Enter RNTI:")
        rnti = int(rnti)

        #prop_1 = input("Is prop_1 true? (y/n)")
        #if prop_1 == "y":
        #    prop_1 = True
        #else:
        #    prop_1 = False
        #prop_2 = float(input("Enter prop_2 (float)")) 
        
        #rnti = int(input("Enter RNTI: "))

        force_mcs = input("Force MCS? (y/n): ") == "y"
        target_mcs = int(input("Target MCS: "))

        control_buffer = e2sm_control_request_buffer(rnti, force_mcs, target_mcs)
        connector.send_e2ap_control_request(control_buffer, gnb)
        print("Control request sent, waiting 1 second before repeating the loop...")



def e2sm_report_request_buffer():
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    return buf

def e2sm_control_request_buffer(rnti, force_mcs, target_mcs):
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.CONTROL
    inner_mess = RAN_control_request()
    
    # ue list map entry
    ue_list_control_element = RAN_param_map_entry()
    ue_list_control_element.key = RAN_parameter.UE_LIST
    
    # ue list message 
    ue_list_message = ue_list_m()
    ue_list_message.connected_ues = 1 # this will not be processed by the gnb, it can be anything

    # ue info message
    ue_info_message = ue_info_m()
    ue_info_message.rnti = rnti
    #ue_info_message.prop_1 = prop_1
    #ue_info_message.prop_2 = prop_2 
    ue_info_message.force_mcs = force_mcs
    ue_info_message.target_mcs = target_mcs

    # put info message into repeated field of ue list message
    ue_list_message.ue_info.extend([ue_info_message])

    # put ue_list_message into the value of the control map entry
    ue_list_control_element.ue_list.CopyFrom(ue_list_message)

    # finalize and send
    inner_mess.target_param_map.extend([ue_list_control_element])
    master_mess.ran_control_request.CopyFrom(inner_mess)
    buf = master_mess.SerializeToString()
    return buf

if __name__ == "__main__":
    xappLogic()
