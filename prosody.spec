%define sslkey /etc/prosody/certs/localhost.key
%define sslcert /etc/prosody/certs/localhost.crt
Summary:	Flexible communications server for Jabber/XMPP
Name:		prosody
Version:	0.11.5
Release:	0.1
License:	MIT
Group:		Daemons
Source0:	http://prosody.im/downloads/source/%{name}-%{version}.tar.gz
# Source0-md5:	224b9b49bd1a568a9548590ade253dd6
Source1:	%{name}.init
Source2:	%{name}.tmpfiles
Source3:	%{name}.service
Patch0:		%{name}-config.patch
URL:		http://prosody.im/
BuildRequires:	libidn-devel
BuildRequires:	lua53-devel
BuildRequires:	openssl-devel
BuildRequires:	rpmbuild(macros) >= 1.647
BuildRequires:	sed >= 4.0
BuildRequires:	systemd-units
Requires:	lua-dbi
Requires:	lua-expat
Requires:	lua-filesystem
Requires:	lua-sec
Requires:	systemd-units >= 0.38
Requires(post,preun,postun):	systemd-units >= 38
Requires(pre):	/usr/sbin/groupadd
Requires(pre):	/usr/sbin/useradd
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
Prosody is a flexible communications server for Jabber/XMPP written in
Lua. It aims to be easy to use, and light on resources. For developers
it aims to be easy to extend and give a flexible system on which to
rapidly develop added functionality, or prototype new protocols.

%prep
%setup -q
%patch -P0 -p1
# fix wrong end of line encoding
%undos doc/stanza.txt doc/session.txt doc/roster_format.txt

%build
./configure \
	--prefix=%{_prefix} \
	--libdir=%{_libdir} \
	--with-lua-include=%{_includedir}/lua5.3 \
	--lua-suffix=5.3 \
	--runwith=lua5.3 \
	--c-compiler="%{__cc}" \
	--cflags="%{rpmcppflags} %{rpmcflags} -fPIC -Wall -D_GNU_SOURCE" \
	--ldflags="%{rpmldflags} -shared"
%{__make}

sed -i -e '1c #!/usr/bin/lua5.3' prosody.install
sed -i -e '1c #!/usr/bin/lua5.3' prosodyctl.install

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT

# fix perms
chmod -x $RPM_BUILD_ROOT%{_libdir}/%{name}/%{name}.version

# avoid rpmlint unstripped-binary-or-object warnings
chmod 0755 $RPM_BUILD_ROOT%{_libdir}/%{name}/util/*.so

# directories for datadir and pids
install -d $RPM_BUILD_ROOT{%{_sharedstatedir}/%{name},/run/%{name}}

# systemd stuff
install -d $RPM_BUILD_ROOT%{systemdunitdir}
cp -p %{SOURCE3} $RPM_BUILD_ROOT%{systemdunitdir}/%{name}.service

# tmpfiles.d stuff
install -d $RPM_BUILD_ROOT%{systemdtmpfilesdir}
cp -p %{SOURCE2} $RPM_BUILD_ROOT%{systemdtmpfilesdir}/%{name}.conf

# install initd script
install -d $RPM_BUILD_ROOT/etc/rc.d/init.d
install -p %{SOURCE1} $RPM_BUILD_ROOT/etc/rc.d/init.d/%{name}

rm $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/certs/*

%clean
rm -rf $RPM_BUILD_ROOT

%pre
%groupadd -g 306 prosody
%useradd -u 306 -r -d %{_sharedstatedir}/%{name} -s /bin/false -c "prosody daemo" -g prosody prosody

%preun
if [ "$1" = "0" ]; then
	/sbin/chkconfig --del prosody
	%service -q prosody stop
fi
%systemd_preun prosody.service

%post
umask 077
if [ ! -f %{sslkey} ]; then
	%{_bindir}/openssl genrsa 2048 > %{sslkey} 2> /dev/null
	chown root:%{name} %{sslkey}
	chmod 640 %{sslkey}
fi

if [ ! -f %{sslcert} ]; then
	FQDN=`hostname`
	if [ "x${FQDN}" = "x" ]; then
		FQDN=localhost.localdomain
	fi

	cat <<-CERT | %{_bindir}/openssl req -new -key %{sslkey} \
	 -x509 -days 365 \
	 -out %{sslcert} 2>/dev/null
	--
	SomeState
	SomeCity
	SomeOrganization
	SomeOrganizationalUnit
	${FQDN}
	root@${FQDN}
	CERT
	chmod 644 %{sslcert}
fi

/sbin/chkconfig --add prosody
%service prosody restart
%systemd_post prosody.service

%postun
if [ "$1" = "0" ]; then
	%userremove %{name}
	%groupremove http
fi
%systemd_reload

%files
%defattr(644,root,root,755)
%doc AUTHORS COPYING HACKERS README TODO doc/*
%attr(755,root,root) %{_bindir}/%{name}
%attr(755,root,root) %{_bindir}/%{name}ctl
%{_mandir}/man1/*.1*
%attr(754,root,root) /etc/rc.d/init.d/%{name}
%dir %{_libdir}/%{name}
%{_libdir}/%{name}/core
%{_libdir}/%{name}/modules
%{_libdir}/%{name}/net
%dir %{_libdir}/%{name}/util
%{_libdir}/%{name}/util/*.lua
%attr(755,root,root) %{_libdir}/%{name}/util/*.so
%{_libdir}/%{name}/util/sasl
%{_libdir}/%{name}/prosody.version
%dir %{_sysconfdir}/%{name}
%dir %{_sysconfdir}/%{name}/certs
%config(noreplace) %attr(640,root,prosody) %{_sysconfdir}/%{name}/prosody.cfg.lua
%{systemdtmpfilesdir}/prosody.conf
%{systemdunitdir}/prosody.service
%dir %attr(755,prosody,prosody) %{_sharedstatedir}/prosody
%dir %attr(710,prosody,prosody) /run/prosody
