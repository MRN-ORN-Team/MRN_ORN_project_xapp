from time import sleep
from ricxappframe.e2ap.asn1 import IndicationMsg
from ran_messages_pb2 import *
import src.e2ap_xapp as e2ap_xapp

# Project 2 Parameters
BER_THRESHOLD = 0.05      # BER threshold
TARGET_LOW_MCS = 2         # Target low MCS to force
MONITORING_INTERVAL = 0.5  # 500ms monitoring interval


def e2sm_report_request_buffer():
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.INDICATION_REQUEST
    inner_mess = RAN_indication_request()
    inner_mess.target_params.extend([RAN_parameter.GNB_ID, RAN_parameter.UE_LIST])
    master_mess.ran_indication_request.CopyFrom(inner_mess)
    return master_mess.SerializeToString()


def e2sm_control_request_buffer(rnti, force_mcs, target_mcs):
    master_mess = RAN_message()
    master_mess.msg_type = RAN_message_type.CONTROL
    inner_mess = RAN_control_request()

    ue_list_control_element = RAN_param_map_entry()
    ue_list_control_element.key = RAN_parameter.UE_LIST

    ue_list_message = ue_list_m()
    ue_list_message.connected_ues = 1

    ue_info_message = ue_info_m()
    ue_info_message.rnti = rnti
    ue_info_message.force_mcs = force_mcs        # True to force MCS, False for normal operation
    ue_info_message.target_mcs = int(target_mcs) # Target MCS value

    ue_list_message.ue_info.extend([ue_info_message])
    ue_list_control_element.ue_list.CopyFrom(ue_list_message)

    inner_mess.target_param_map.extend([ue_list_control_element])
    master_mess.ran_control_request.CopyFrom(inner_mess)
    return master_mess.SerializeToString()


def xappLogic():
    connector = e2ap_xapp.e2apXapp()
    gnb_id_list = connector.get_gnb_id_list()

    if not gnb_id_list:
        print("No connected gNB found.")
        return

    gnb = gnb_id_list[0]
    report_req_buffer = e2sm_report_request_buffer()
    print(f"Target gNB: {gnb} - Starting monitoring...")

    while True:
        # 1. Send periodic metric request to gNB
        connector.send_e2ap_control_request(report_req_buffer, gnb)

        # 2. Wait for the monitoring interval
        sleep(MONITORING_INTERVAL)

        # 3. Read incoming response with radio metrics
        messgs = connector.get_queued_rx_message()
        for msg in messgs:
            if msg["message type"] == connector.RIC_IND_RMR_ID:
                indm = IndicationMsg()
                indm.decode(msg["payload"])
                resp = RAN_indication_response()
                resp.ParseFromString(indm.indication_message)

                for entry in resp.param_map:
                    if entry.HasField("ue_list"):
                        for ue in entry.ue_list.ue_info:
                            rnti = ue.rnti
                            current_ber = ue.dl_ber
                            mcs = ue.current_mcs

                            # BER check and MCS decision logic
                            if current_ber < BER_THRESHOLD:
                                print(
                                    f"[UE {rnti}] BER={current_ber:.4f} < {BER_THRESHOLD} "
                                    f"(Current MCS={mcs}) -> FORCING MCS={TARGET_LOW_MCS}"
                                )
                                ctrl_buf = e2sm_control_request_buffer(
                                    rnti, force_mcs=True, target_mcs=TARGET_LOW_MCS
                                )
                            else:
                                print(
                                    f"[UE {rnti}] BER={current_ber:.4f} >= {BER_THRESHOLD} "
                                    f"(Current MCS={mcs}) -> NORMAL OPERATION"
                                )
                                ctrl_buf = e2sm_control_request_buffer(
                                    rnti, force_mcs=False, target_mcs=0
                                )

                            # Send control command to gNB
                            connector.send_e2ap_control_request(ctrl_buf, gnb)


if __name__ == "__main__":
    xappLogic()