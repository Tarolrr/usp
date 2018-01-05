# **************************************************************************
# WT-369 USP Message Protocol Buffer Schema
#
#  Copyright (c) 2017, Broadband Forum
#
#  The undersigned members have elected to grant the copyright to
#  their contributed material used in this software:
#    Copyright (c) 2017 ARRIS Enterprises, LLC.
#
# This is draft software, is subject to change, and has not been approved
#  by members of the Broadband Forum. It is made available to non-members
#  for internal study purposes only. For such study purposes, you have the
#  right to make copies and modifications only for distributing this software
#  internally within your organization among those who are working on it
#  (redistribution outside of your organization for other than study purposes
#  of the original or modified works is not permitted). For the avoidance of
#  doubt, no patent rights are conferred by this license.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
#  THE POSSIBILITY OF SUCH DAMAGE.
#
# Unless a different date is specified upon issuance of a draft software
#  release, all member and non-member license rights under the draft software
#  release will expire on the earliest to occur of (i) nine months from the
#  date of issuance, (ii) the issuance of another version of the same software
#  release, or (iii) the adoption of the draft software release as final.
#
# BBF software release registry: http:##www.broadband-forum.org/software
# **************************************************************************

"""
#
# File Name: stomp_client.py
#
# Description: A STOMP Client for sending STOMP messages to and receiving
#               STOMP messages from a USP Endpoint
#
"""

import logging

import stomp

from mtp_proxy import utils


class MyStompConnListener(stomp.ConnectionListener):
    """A STOMP Connection Listener for receiving USP messages"""
    def __init__(self, queue):
        """Initialize our STOMP Connection Listener"""
        stomp.ConnectionListener.__init__(self)
        self._queue = queue
        self._logger = logging.getLogger(self.__class__.__name__)

    def on_error(self, headers, message):
        """STOMP Connection Listener - handle errors"""
        self._logger.error("Received an error [%s]", message)

    def on_message(self, headers, body):
        """STOMP Connection Listener - record messages to the incoming queue"""
        self._logger.info("Received a STOMP message on my USP Message Queue")
        self._logger.debug("Payload received: [%s]", body)

        # Validate the STOMP Headers
        if "content-type" in headers:
            self._logger.debug("Validating the STOMP Headers for 'content-type'")
            if headers["content-type"].startswith("application/vnd.bbf.usp.msg+json"):
                self._logger.debug("STOMP Message has an acceptable 'content-type'")
                self._queue.push(body)
            elif headers["content-type"].startswith("application/vnd.bbf.usp.msg"):
                self._logger.debug("STOMP Message has a proper 'content-type'")
                self._queue.push(body)
            else:
                self._logger.warning("Incoming STOMP message contained an Unsupported Content-Type: %s",
                                     headers["content-type"])
        else:
            self._logger.warning("Incoming STOMP message had no Content-Type")


class StompClient(object):
    """A STOMP to USP Binding"""
    def __init__(self, host="127.0.0.1", port=61613, username="admin", password="admin", virtual_host="/",
                 outgoing_heartbeats=0, incoming_heartbeats=0):
        """Initialize the STOMP USP Binding for a USP Endpoint
            - 61613 is the default STOMP port for RabbitMQ installations"""
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._queue = utils.GenericReceivingQueue()
        self._listener = MyStompConnListener(self._queue)
        self._logger = logging.getLogger(self.__class__.__name__)

        # We don't want to decode the payload, so use auto_decode=False
        self._conn = stomp.Connection12([(host, port)], heartbeats=(outgoing_heartbeats, incoming_heartbeats),
                                        vhost=virtual_host, auto_decode=False)
        self._conn.set_listener("defaultListener", self._listener)
        self._conn.start()
        self._conn.connect(username, password, wait=True)

    def listen(self, my_addr):
        """Listen to a STOMP destination for incoming messages"""
        msg_id = 1

        #TODO: Handle the ID Better
        # Need a unique ID per destination being subscribed to
        # Need to associate a self-generated (and unique) ID to the destination
        # Need to store that destination and it's ID in a dictionary
        # Need a stop_listening(self, dest) method
        #   - Bulld the full destination: self._build_dest(dest)
        #   - Retrieve the ID from the dictionary for the destination
        #   - Unsubscribe: self._conn.unsubscribe(id)
        self._conn.subscribe(my_addr, id=str(msg_id), ack="auto")
        self._logger.info("Subscribed to Destination: %s", my_addr)

    def get_msg(self, timeout_in_seconds=-1):
        """Retrieve a message from the queue"""
        return self._queue.get_msg(timeout_in_seconds)

    def send_msg(self, my_addr, payload, to_addr):
        """Send the ProtoBuf Serialized message to the provided STOMP address"""
        content_type = "application/vnd.bbf.usp.msg"
        usp_headers = {"reply-to-dest": my_addr}
        self._logger.debug("Using [%s] as the value of the reply-to-dest header", my_addr)
        self._conn.send(to_addr, payload, content_type, usp_headers)
        self._logger.info("Sending a STOMP message to the following address: %s", to_addr)

    def clean_up(self):
        """Clean up the STOMP Connection"""
        self._conn.disconnect()
