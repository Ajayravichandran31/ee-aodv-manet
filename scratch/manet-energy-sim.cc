/*
 * manet-energy-sim.cc
 * ---------------------------------------------------------------------
 * Final-year project scenario: Energy-Efficient Routing Optimization
 * in MANETs for Battery-Constrained Devices.
 *
 * Compares baseline AODV vs EE-AODV (your energy-aware clone module)
 * under identical mobility/traffic/energy conditions.
 *
 * OUTPUTS (per run):
 *   - <prefix>-flowmon.xml     FlowMonitor stats (PDR, delay, throughput)
 *   - <prefix>-energy.csv      Per-node residual energy every second
 *   - <prefix>-netanim.xml     NetAnim animation trace (open in NetAnim,
 *                               or screen-record it -> video, see guide)
 *
 * USAGE:
 *   ./ns3 run "manet-energy-sim --protocol=aodv   --nNodes=30 --prefix=aodv"
 *   ./ns3 run "manet-energy-sim --protocol=eeaodv --nNodes=30 --prefix=eeaodv"
 *
 * Place this file in scratch/manet-energy-sim.cc
 * ---------------------------------------------------------------------
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/aodv-module.h"
#include "ns3/energy-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"

// If your cloned energy-aware module is named "eeaodv", uncomment:
 #include "ns3/eeaodv-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("ManetEnergySim");

// ---- Globals used by the periodic energy logger ----
static std::ofstream g_energyStream;
static NodeContainer g_nodes;
static double g_initialEnergyJ = 100.0;

void
LogResidualEnergy()
{
  uint32_t aliveCount = 0;
  g_energyStream << Simulator::Now().GetSeconds();
  for (uint32_t i = 0; i < g_nodes.GetN(); ++i)
    {
      Ptr<Node> node = g_nodes.Get(i);
      Ptr<EnergySourceContainer> esc = node->GetObject<EnergySourceContainer>();
      double rem = 0.0;
      if (esc && esc->GetN() > 0)
        {
          rem = esc->Get(0)->GetRemainingEnergy();
        }
      if (rem > 0.001)
        {
          aliveCount++;
        }
      g_energyStream << "," << rem;
    }
  g_energyStream << "," << aliveCount << std::endl;

  Simulator::Schedule(Seconds(1.0), &LogResidualEnergy);
}

int
main(int argc, char* argv[])
{
  // --------------------- Configurable parameters ---------------------
  uint32_t nNodes = 30;
  double simTime = 200.0;       // seconds
  double areaX = 1000.0;        // metres
  double areaY = 1000.0;
  uint32_t nFlows = 10;         // number of CBR source-destination pairs
  double packetInterval = 0.25; // seconds between packets per flow
  uint32_t packetSize = 512;    // bytes
  std::string protocol = "aodv"; // "aodv" or "eeaodv"
  std::string prefix = "aodv";
  uint32_t runNumber = 1;

  CommandLine cmd;
  cmd.AddValue("nNodes", "Number of MANET nodes", nNodes);
  cmd.AddValue("areaX", "Area width (m)", areaX);
  cmd.AddValue("areaY", "Area height (m)", areaY);
  cmd.AddValue("simTime", "Simulation duration (s)", simTime);
  cmd.AddValue("nFlows", "Number of CBR flows", nFlows);
  cmd.AddValue("protocol", "Routing protocol: aodv | eeaodv", protocol);
  cmd.AddValue("prefix", "Output file prefix", prefix);
  cmd.AddValue("initialEnergy", "Initial battery energy per node (J)", g_initialEnergyJ);
  cmd.AddValue("run", "RNG run number (vary for repeated trials)", runNumber);
  cmd.Parse(argc, argv);

  RngSeedManager::SetRun(runNumber);

  g_nodes.Create(nNodes);

  // --------------------- Mobility (Random Waypoint) --------------------
  MobilityHelper mobility;
  mobility.SetPositionAllocator("ns3::RandomRectanglePositionAllocator",
                                 "X", StringValue("ns3::UniformRandomVariable[Min=0|Max=" +
                                                   std::to_string(areaX) + "]"),
                                 "Y", StringValue("ns3::UniformRandomVariable[Min=0|Max=" +
                                                   std::to_string(areaY) + "]"));
  mobility.SetMobilityModel("ns3::RandomWaypointMobilityModel",
                             "Speed", StringValue("ns3::UniformRandomVariable[Min=1.0|Max=5.0]"),
                             "Pause", StringValue("ns3::ConstantRandomVariable[Constant=2.0]"),
                             "PositionAllocator",
                             StringValue("ns3::RandomRectanglePositionAllocator"));
  mobility.Install(g_nodes);
  for (uint32_t i = 0; i < g_nodes.GetN(); ++i) { Vector pos = g_nodes.Get(i)->GetObject<MobilityModel>()->GetPosition(); std::cout << "Node " << i << " pos: " << pos << std::endl; }

  // --------------------- WiFi ad hoc PHY/MAC ---------------------------
  WifiHelper wifi;
  wifi.SetStandard(WIFI_STANDARD_80211b);
  wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager", "DataMode", StringValue("DsssRate1Mbps"), "ControlMode", StringValue("DsssRate1Mbps"), "RtsCtsThreshold", UintegerValue(2200));

  YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
  YansWifiPhyHelper phy;
  phy.SetChannel(channel.Create());
  // TxPower affects both range AND energy draw -- keep modest for a MANET scenario
  phy.Set("TxPowerStart", DoubleValue(16.0));
  phy.Set("TxPowerEnd", DoubleValue(16.0));

  WifiMacHelper mac;
  mac.SetType("ns3::AdhocWifiMac");

  NetDeviceContainer devices = wifi.Install(phy, mac, g_nodes);
  phy.EnablePcapAll(prefix);

  // --------------------- Energy model -----------------------------------
  BasicEnergySourceHelper energySourceHelper;
  energySourceHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(g_initialEnergyJ));
  EnergySourceContainer energySources = energySourceHelper.Install(g_nodes);

  WifiRadioEnergyModelHelper radioEnergyHelper;
  radioEnergyHelper.Set("TxCurrentA", DoubleValue(0.017));
  radioEnergyHelper.Set("RxCurrentA", DoubleValue(0.0197));
  radioEnergyHelper.Set("IdleCurrentA", DoubleValue(0.0003));
  DeviceEnergyModelContainer deviceModels =
      radioEnergyHelper.Install(devices, energySources);

  // --------------------- Internet stack + routing ------------------------
  InternetStackHelper internet;

  if (protocol == "eeaodv")
    {
      EeaodvHelper eeaodv;
      internet.SetRoutingHelper(eeaodv);
    }
  else
    {
      AodvHelper aodv;
      internet.SetRoutingHelper(aodv);
    }
  internet.Install(g_nodes);

  Ipv4AddressHelper address;
  address.SetBase("10.0.0.0", "255.255.255.0");
  Ipv4InterfaceContainer interfaces = address.Assign(devices);

  // --------------------- Traffic: CBR flows over UDP ----------------------
  uint16_t basePort = 9000;
  ApplicationContainer sinkApps, sourceApps;
  Ptr<UniformRandomVariable> pairRv = CreateObject<UniformRandomVariable>();

  for (uint32_t i = 0; i < nFlows; ++i)
    {
      uint32_t srcIdx = pairRv->GetInteger(0, nNodes - 1);
      uint32_t dstIdx = pairRv->GetInteger(0, nNodes - 1);
      while (dstIdx == srcIdx)
        {
          dstIdx = pairRv->GetInteger(0, nNodes - 1);
        }

      uint16_t port = basePort + i;
      PacketSinkHelper sink("ns3::UdpSocketFactory",
                             InetSocketAddress(Ipv4Address::GetAny(), port));
      sinkApps.Add(sink.Install(g_nodes.Get(dstIdx)));

      OnOffHelper onoff("ns3::UdpSocketFactory",
                         InetSocketAddress(interfaces.GetAddress(dstIdx), port));
      onoff.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1000]"));
      onoff.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
      onoff.SetAttribute("DataRate",
                          DataRateValue(DataRate(static_cast<uint64_t>(
                              (packetSize * 8) / packetInterval))));
      onoff.SetAttribute("PacketSize", UintegerValue(packetSize));
      std::cout << "Flow " << i << ": src=" << srcIdx << " dst=" << dstIdx << " target=" << interfaces.GetAddress(dstIdx) << ":" << port << std::endl;
      ApplicationContainer app = onoff.Install(g_nodes.Get(srcIdx));
      app.Start(Seconds(pairRv->GetValue(2.0, 5.0)));
      app.Stop(Seconds(simTime - 5.0));
      sourceApps.Add(app);
    }
  sinkApps.Start(Seconds(0.0));
  sinkApps.Stop(Seconds(simTime));

  // --------------------- FlowMonitor --------------------------------------
  FlowMonitorHelper flowmonHelper;
  Ptr<FlowMonitor> flowMonitor = flowmonHelper.InstallAll();

  // --------------------- Energy logging (for network lifetime graphs) -----
  g_energyStream.open(prefix + "-energy.csv");
  g_energyStream << "time_s";
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      g_energyStream << ",node" << i << "_J";
    }
  g_energyStream << ",aliveNodes" << std::endl;
  Simulator::Schedule(Seconds(1.0), &LogResidualEnergy);

  // --------------------- NetAnim (for the animation/video) ----------------
  AnimationInterface anim(prefix + "-netanim.xml");
  anim.SetMaxPktsPerTraceFile(500000);
  anim.EnablePacketMetadata(true);

  // --------------------- Run --------------------------------------------
  Simulator::Stop(Seconds(simTime));
  Simulator::Run();
  for (uint32_t i = 0; i < sinkApps.GetN(); ++i) { Ptr<PacketSink> sinkPtr = DynamicCast<PacketSink>(sinkApps.Get(i)); std::cout << "Sink " << i << " received bytes: " << sinkPtr->GetTotalRx() << std::endl; }

  flowMonitor->SerializeToXmlFile(prefix + "-flowmon.xml", true, true);
  g_energyStream.close();

  Simulator::Destroy();
  return 0;
}
