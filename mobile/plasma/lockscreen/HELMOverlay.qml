import QtQuick

Item {
    id: root

    anchors.fill: parent
    z: 10000

    property string currentTime: ""
    property string currentDate: ""
    property bool pulseState: false

    function updateClock() {
        const now = new Date()

        currentTime = Qt.formatTime(now, "HH:mm:ss")
        currentDate = Qt.formatDate(now, "yyyy-MM-dd")
    }

    Component.onCompleted: updateClock()

    Timer {
        interval: 1000
        running: true
        repeat: true

        onTriggered: {
            root.updateClock()
            root.pulseState = !root.pulseState
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: "#2242E8FF"
        border.width: 1
    }

    Rectangle {
        id: identityPanel

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 38
        anchors.topMargin: 38

        width: Math.min(570, parent.width * 0.43)
        height: 166

        color: "#FF02070B"
        border.color: "#42E8FF"
        border.width: 1

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 7
            color: "#42E8FF"
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 22
            anchors.rightMargin: 18
            anchors.topMargin: 17
            height: 1
            color: "#6642E8FF"
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 28
            anchors.rightMargin: 18
            anchors.topMargin: 28
            spacing: 7

            Text {
                text: "HELM MOBILE // SECURITY LOCK"
                color: "#42E8FF"
                font.family: "Hack"
                font.pixelSize: 18
                font.bold: true
                font.letterSpacing: 1.2
            }

            Text {
                text: "CYBERDECK-LAPTOP  ·  FIELD NODE 01"
                color: "#D7F9FF"
                font.family: "Hack"
                font.pixelSize: 12
                font.bold: true
                font.letterSpacing: 0.65
            }

            Text {
                text: "KSCREENLOCKER AUTHENTICATION  //  NATIVE CHANNEL"
                color: "#78A8B3"
                font.family: "Hack"
                font.pixelSize: 11
                font.letterSpacing: 0.35
            }

            Text {
                text: "SESSION SEALED  ·  AUTHENTICATION REQUIRED"
                color: "#3EC9DC"
                font.family: "Hack"
                font.pixelSize: 10
                font.letterSpacing: 0.3
            }
        }

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 14
            anchors.bottomMargin: 12
            width: 62
            height: 3
            color: "#42E8FF"
        }
    }

    Rectangle {
        id: authFrame

        anchors.centerIn: parent
        anchors.verticalCenterOffset: 20

        width: 440
        height: 420

        color: "#A802070B"

        border.color:
            root.pulseState
            ? "#7542E8FF"
            : "#4942E8FF"

        border.width: 1
        radius: 2

        Behavior on border.color {
            ColorAnimation { duration: 450 }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 4
            color: "#42E8FF"
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 10
            color: "transparent"
            border.color: "#1642E8FF"
            border.width: 1
        }

        Text {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 18

            text: "SECURE SESSION CHANNEL"
            color: "#42E8FF"

            font.family: "Hack"
            font.pixelSize: 10
            font.bold: true
            font.letterSpacing: 0.8
        }

        Item {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 50

            width: 86
            height: 86

            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: "#07151C"
                border.color: "#42E8FF"
                border.width: 2

                Text {
                    anchors.centerIn: parent
                    text: "D"
                    color: "#DDFBFF"
                    font.family: "Hack"
                    font.pixelSize: 36
                    font.bold: true
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                width: 20
                height: 20
                radius: width / 2
                color: "#42E8FF"
                border.color: "#02070B"
                border.width: 3
            }
        }

        Text {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 148

            text: "DARIUSZ"
            color: "#F2FDFF"

            font.family: "Hack"
            font.pixelSize: 23
            font.bold: true
            font.letterSpacing: 1.2
        }

        Text {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 20

            text: "NATIVE KSCREENLOCKER CREDENTIAL FLOW"
            color: "#397E8A"

            font.family: "Hack"
            font.pixelSize: 8
            font.bold: true
            font.letterSpacing: 0.35
        }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 38
        anchors.bottomMargin: 132

        width: 318
        height: 104

        color: "#FC02070B"
        border.color: "#5555DDF3"
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 5

            Text {
                text: root.currentTime
                color: "#E6FCFF"
                font.family: "Hack"
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 1.4
            }

            Text {
                text: root.currentDate + "  //  WAYLAND SECURE SESSION"
                color: "#69A5B1"
                font.family: "Hack"
                font.pixelSize: 9
                font.letterSpacing: 0.25
            }

            Text {
                text: "STATUS: SESSION SEALED"

                color:
                    root.pulseState
                    ? "#42E8FF"
                    : "#268D9D"

                font.family: "Hack"
                font.pixelSize: 10
                font.bold: true
                font.letterSpacing: 0.45

                Behavior on color {
                    ColorAnimation { duration: 450 }
                }
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin: 38
        anchors.bottomMargin: 48
        width: 180
        height: 2
        color: "#42E8FF"
    }
}
