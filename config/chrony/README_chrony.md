# Chrony Setup Notes

This MVP assumes:

- UGV acts as the Chrony server
- UAV and other ground nodes act as Chrony clients

The files in this folder are examples only. Replace the example subnet and IP values with the real network plan before deployment.

## First check whether chrony tools exist

```bash
which chronyc
./scripts/check_chrony.sh
```

If `which chronyc` prints nothing, Chrony is not installed or not on PATH yet.

In that case:

- install Chrony first
- or document that time sync has not been enabled yet, then revisit this step before real dual-machine latency testing

## Server side

1. Copy `config/chrony/chrony_server.conf` into your Chrony configuration path.
2. Restart Chrony.
3. Verify with:

```bash
chronyc tracking
chronyc sources
```

Or use:

```bash
./scripts/check_chrony.sh
```

## Client side

1. Copy `config/chrony/chrony_client.conf` into your Chrony configuration path.
2. Replace `192.168.0.10` with the real UGV IP.
3. Restart Chrony.
4. Verify with:

```bash
chronyc tracking
chronyc sources
```

Or use:

```bash
./scripts/check_chrony.sh
```

## Why this matters here

The mock nodes stamp `source_stamp` in each probe and map tile message. Good clock sync keeps latency measurements meaningful when the system is later split across machines.
