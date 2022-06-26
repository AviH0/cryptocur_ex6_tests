from scripts.network import Network
from scripts.node import LightningNode
import scripts.utils
from scripts.utils import APPEAL_PERIOD, EthereumAddress, sign, ChannelStateMessage
from brownie import chain, Channel, accounts, history  # type: ignore
from brownie.exceptions import VirtualMachineError  # type: ignore
from malicious_functions import *
import pytest


ONE_ETH: int = 10**18

def test_exteral_non_malicous_send_works_as_expected(alice: LightningNode, bob: LightningNode, network: Network):
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    # Alice sends money thrice
    hist = len(history)
    send_valid_balance_on_own_channel(network, bob.get_ip_address(), alice, chan_address, ONE_ETH)
    assert hist == len(history)

    # BOB CLOSING UNILATERALLY
    bob.close_channel(chan_address)

    # waiting
    chain.mine(APPEAL_PERIOD)
    assert Channel.at(chan_address).balance() == 10 * ONE_ETH

    # Bob Withdraws
    bob.withdraw_funds(chan_address)
    assert Channel.at(chan_address).balance() == 9 * ONE_ETH

    # Alice Withdraws
    alice.withdraw_funds(chan_address)

    assert Channel.at(chan_address).balance() == 0

    assert alice_init_balance == accounts[0].balance() + 1*ONE_ETH
    assert bob_init_balance == accounts[1].balance() - 1*ONE_ETH

def test_transfer_money_without_reducing_own_balance(alice: LightningNode, bob: LightningNode, network: Network) -> None:
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH


    # Alice sends money
    send_without_reducing_own_balance_on_own_channel(network, bob.get_ip_address(), alice, chan_address, ONE_ETH)
    
    alice.close_channel(chan_address)
    bob.appeal_closed_chan(chan_address)

    # Waiting
    chain.mine(APPEAL_PERIOD+2)

    # Bob Withdraws
    bob.withdraw_funds(chan_address)

    # Alice Withdraws
    alice.withdraw_funds(chan_address)

    assert chan.balance() == 0

    assert alice_init_balance == accounts[0].balance()
    assert bob_init_balance == accounts[1].balance()

def test_transfer_money_with_bad_sig(alice: LightningNode, bob: LightningNode, network: Network) -> None:
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    # Alice sends money
    alice.send(chan_address, 1*ONE_ETH)
    send_with_bad_sig_on_own_channel(network, bob.get_ip_address(), alice, chan_address, ONE_ETH)

    alice.close_channel(chan_address)
    bob.appeal_closed_chan(chan_address)

    # Waiting
    chain.mine(APPEAL_PERIOD+2)

    # Bob Withdraws
    bob.withdraw_funds(chan_address)

    # Alice Withdraws
    alice.withdraw_funds(chan_address)

    assert chan.balance() == 0

    assert alice_init_balance == accounts[0].balance() + 1*ONE_ETH
    assert bob_init_balance == accounts[1].balance() - 1*ONE_ETH

def test_transfer_money_bad_serial(alice: LightningNode, bob: LightningNode, network: Network) -> None:
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    # Alice sends money
    alice.send(chan_address, 1*ONE_ETH)
    send_bad_serial_on_own_channel(network, bob.get_ip_address(), alice, chan_address, ONE_ETH)

    alice.close_channel(chan_address)
    bob.appeal_closed_chan(chan_address)

    # Waiting
    chain.mine(APPEAL_PERIOD+2)

    # Bob Withdraws
    bob.withdraw_funds(chan_address)

    # Alice Withdraws
    alice.withdraw_funds(chan_address)

    assert chan.balance() == 0

    assert alice_init_balance == accounts[0].balance() + 1*ONE_ETH
    assert bob_init_balance == accounts[1].balance() - 1*ONE_ETH

def test_close_channel_with_bad_balance(alice: LightningNode, bob: LightningNode, network: Network):
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    with pytest.raises(VirtualMachineError):
        # Alice tries to close channel with bad balance (but signed properly)
        alice.close_channel(chan_address, sign(ChannelStateMessage(chan_address, alice_init_balance, alice_init_balance, 1), bob.get_eth_address()))


def test_give_wrong_ack_own_channel(alice: LightningNode, bob: LightningNode, network: Network):
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    # Alice sends money
    old_state = alice.get_current_channel_state(chan_address)
    alice.send(chan_address, 1*ONE_ETH)
    alice.send(chan_address, 1*ONE_ETH)
    alice.send(chan_address, 1*ONE_ETH)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(LightningNode, 'receive_funds', get_malicious_node_recieve_funds_wrong_amount_own_channel(bob.get_ip_address(), network))
        bob.send(chan_address, 1*ONE_ETH)
    
    # now bob's latest confirmation is invalid, so alice can try close with old state and bob's appeal may fail.

    alice.close_channel(chan_address, old_state)
    bob.appeal_closed_chan(chan_address)

    # Waiting
    chain.mine(APPEAL_PERIOD+2)

    # Bob Withdraws
    bob.withdraw_funds(chan_address)

    # Alice Withdraws
    alice.withdraw_funds(chan_address)

    assert chan.balance() == 0

    assert alice_init_balance == accounts[0].balance() + 3*ONE_ETH
    assert bob_init_balance == accounts[1].balance() - 3*ONE_ETH

def test_give_invalid_ack_own_channel(alice: LightningNode, bob: LightningNode, network: Network):
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    # Alice sends money
    old_state = alice.get_current_channel_state(chan_address)
    alice.send(chan_address, 1*ONE_ETH)
    alice.send(chan_address, 1*ONE_ETH)
    alice.send(chan_address, 1*ONE_ETH)
    with pytest.MonkeyPatch.context() as m:
        m.setattr(LightningNode, 'receive_funds', get_malicious_node_recieve_funds_invalid_amount_own_channel(bob.get_ip_address(), network))
        bob.send(chan_address, 1*ONE_ETH)
    
    # now bob's latest confirmation is invalid, so alice can try close with old state and bob's appeal may fail.

    alice.close_channel(chan_address, old_state)
    bob.appeal_closed_chan(chan_address)

    # Waiting
    chain.mine(APPEAL_PERIOD+2)

    # Bob Withdraws
    bob.withdraw_funds(chan_address)

    # Alice Withdraws
    alice.withdraw_funds(chan_address)

    assert chan.balance() == 0

    assert alice_init_balance == accounts[0].balance() + 3*ONE_ETH
    assert bob_init_balance == accounts[1].balance() - 3*ONE_ETH

def test_notify_channel_bad_appeal_length(alice: LightningNode, bob: LightningNode, network: Network):
    network.stop() 
     # Creating channel
    with pytest.MonkeyPatch.context() as m:
        m.setattr(scripts.node, 'APPEAL_PERIOD', 1)
        chan_address = alice.establish_channel(
            bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
        network.resume()
        m.setattr(scripts.node, 'APPEAL_PERIOD', 5)
        bob.notify_of_channel(chan_address, alice.get_ip_address())
        assert chan_address not in bob.get_list_of_channels()

def test_notify_bob_of_channel_he_established(alice: LightningNode, bob: LightningNode, network: Network):
    network.stop()
    chan_address = bob.establish_channel(
        alice.get_eth_address(), alice.get_ip_address(), 10 * ONE_ETH)
    assert chan_address in bob.get_list_of_channels()
    network.resume()
    # Try to trick bob into thinking he's not the one who established the channel
    bob.notify_of_channel(chan_address, alice.get_ip_address())
    assert chan_address in bob.get_list_of_channels()
    # Now try to trick bob into thinking he's recieving money when in fact he is sending.
    bob.receive_funds(sign(ChannelStateMessage(chan_address, 5*ONE_ETH, 5 * ONE_ETH, 1), alice.get_eth_address()))
    
    # make sure bob didn't save that state message
    assert bob.get_current_channel_state(chan_address).serial_number == 0


def test_close_channel_with_modified_serial(alice: LightningNode, bob: LightningNode, network: Network):
    alice_init_balance = accounts[0].balance()
    bob_init_balance = accounts[1].balance()

    # Creating channel
    chan_address = alice.establish_channel(
        bob.get_eth_address(), bob.get_ip_address(), 10 * ONE_ETH)
    chan = Channel.at(chan_address)
    assert chan.balance() == 10 * ONE_ETH

    alice.send(chan_address, 1*ONE_ETH)
    alice.send(chan_address, 1*ONE_ETH)
    alice.send(chan_address, 1*ONE_ETH)
    state = alice.get_current_channel_state(chan_address)

    with pytest.raises(VirtualMachineError):
        # Alice tries to close channel with modified serial (improperly signed)
        alice.close_channel(chan_address, ChannelStateMessage(chan_address, alice_init_balance, alice_init_balance, 10, state.sig))
