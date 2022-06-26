from scripts.network import Network, Message
from scripts.node import LightningNode
from scripts.utils import APPEAL_PERIOD, EthereumAddress, sign, ChannelStateMessage
from brownie import chain, Channel, accounts, history  # type: ignore
from brownie.exceptions import VirtualMachineError  # type: ignore
import pytest

ONE_ETH: int = 10**18

def send_valid_balance_on_own_channel(net: Network, recipient_ip, node: LightningNode, channel_address: EthereumAddress, amount_in_wei: int) -> None:
    """
    
    """
    latest_state = node.get_current_channel_state(channel_address)
    new_state = ChannelStateMessage(channel_address, latest_state.balance1 - amount_in_wei, latest_state.balance2 + amount_in_wei, latest_state.serial_number + 1)
    new_state = sign(new_state, node.get_eth_address())
    net.send_message(recipient_ip, Message.RECEIVE_FUNDS, new_state)

def send_without_reducing_own_balance_on_own_channel(net: Network, recipient_ip, node: LightningNode, channel_address: EthereumAddress, amount_in_wei: int) -> None:
    """
    
    """
    latest_state = node.get_current_channel_state(channel_address)
    new_state = ChannelStateMessage(channel_address, latest_state.balance1, latest_state.balance2 + amount_in_wei, latest_state.serial_number + 1)
    new_state = sign(new_state, node.get_eth_address())
    net.send_message(recipient_ip, Message.RECEIVE_FUNDS, new_state)

def send_with_bad_sig_on_own_channel(net: Network, recipient_ip, node: LightningNode, channel_address: EthereumAddress, amount_in_wei: int) -> None:
    """
    
    """
    latest_state = node.get_current_channel_state(channel_address)
    new_state = ChannelStateMessage(channel_address, latest_state.balance1 - amount_in_wei, latest_state.balance2 + amount_in_wei, latest_state.serial_number + 1, latest_state.sig)
    net.send_message(recipient_ip, Message.RECEIVE_FUNDS, new_state)

def send_bad_serial_on_own_channel(net: Network, recipient_ip, node: LightningNode, channel_address: EthereumAddress, amount_in_wei: int) -> None:
    """
    
    """
    latest_state = node.get_current_channel_state(channel_address)
    new_state = ChannelStateMessage(channel_address, latest_state.balance1 - amount_in_wei, latest_state.balance2 + amount_in_wei, latest_state.serial_number - 1)
    new_state = sign(new_state, node.get_eth_address())
    net.send_message(recipient_ip, Message.RECEIVE_FUNDS, new_state)

def get_malicious_node_recieve_funds_wrong_amount_own_channel(transferer_ip, network):
    def recieve(self, state_msg: ChannelStateMessage):
        """
        A method that is called when to notify this node that it receives funds through the channel.
        Assume msg is valid, send a bad ack (try to steal 0.1 ETH from the other node)
        """
        network.send_message(transferer_ip, Message.ACK_TRANSFER, 
        sign(ChannelStateMessage(state_msg.contract_address, state_msg.balance1 + int(0.1*ONE_ETH), state_msg.balance2 - int(0.1*ONE_ETH), state_msg.serial_number + 1), self.get_eth_address()))
    return recieve


def get_malicious_node_recieve_funds_invalid_amount_own_channel(transferer_ip, network):
    def recieve(self, state_msg: ChannelStateMessage):
        """
        A method that is called when to notify this node that it receives funds through the channel.
        Assume msg is valid, send a bad ack.
        """
        latest_state = self.get_current_channel_state(state_msg.contract_address)
        network.send_message(transferer_ip, Message.ACK_TRANSFER, 
        sign(ChannelStateMessage(state_msg.contract_address, latest_state.balance1, state_msg.balance2, state_msg.serial_number + 1), self.get_eth_address()))
    return recieve

def malicious_init_channel_state_message(self, channel_address: EthereumAddress, balance1: int, balance2: int, serial_number: int) -> None:
    """
    
    """
    self.channel_address = channel_address
    self.balance1 = balance1 + ONE_ETH
    self.balance2 = balance2
    self.serial_number = serial_number
    self.signature = ''
    self.signature = sign(self, LightningNode.get_eth_address())
    return self

